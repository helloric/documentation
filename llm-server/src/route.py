import os

from flask import Flask, request, Response
from stt import STT
from llm.llm import LLM
from llm.chat_history import ChatHistory
from tts import TTSWrapper, THORSTEN_DE_SPEAKER_EMOTION_MAP
from parsing.parser import Parser, ParseException, ResultException
from parsing.expression import SpeechExpression, MoveExpression, Expression
from parsing.token import Emotion
from util import RestMaybe, get_resource
from typing import List, TypedDict, cast
from waitress import serve
import base64
import json


class VoiceRequest(TypedDict):
    valence: int
    arousal: int
    b64audio: str


class TextRequest(TypedDict):
    valence: int
    arousal: int
    text: str

class CommandRequest(TypedDict):
    valence: int
    arousal: int
    command_id: int
    payload: object

class UpdateExhibitKeysRequest(TypedDict):
    keys: "list[str]"


class UpdateExhibitContextRequest(TypedDict):
    exhibit_key: str


SERVER_PORT = os.environ.get('HRIC_HTTP_PORT', '5000')

stt = STT(get_resource('stt/audio_files'), 'large')
llm = LLM('llama3.1', language='en')
#base_speaker=get_resource('tts/thorsten-model'), emotion_map=THORSTEN_DE_SPEAKER_EMOTION_MAP
tts = TTSWrapper(reference_speaker=get_resource('tts/references/speaker2.mp3'))
#tts = TTSWrapper.get_melo(get_resource('tts/references/speaker2.mp3'), get_resource('tts/thorsten-model'), 'EN', speaker_map=THORSTEN_DE_SPEAKER_EMOTION_MAP)

app = Flask('llm-server')


@app.route('/hric/llm/command', methods=['POST'])
def accept_command():
    return (
        RestMaybe(request)
        .wellformed()
        .exists('valence')
        .exists('arousal')
        .exists('command_id')
        .optional('payload')
        .run(lambda _, request_data: _accept_command(request_data))
    )

def _accept_command(request_data: CommandRequest):
    valence = request_data['valence']
    arousal = request_data['arousal']
    command_id = request_data['command_id']
    if command_id < 0 or command_id >= len(llm.prompt_manager.commands):
        return ({'error': f'Invalid Command ID: {command_id}. Allowed range: 0-{len(llm.prompt_manager.commands)}'}, 403)
    
    if command_id <= 1:
        payload = request_data.get('payload', '')
        print(llm.prompt_manager.commands[command_id])
        return _text_to_array({'text': llm.prompt_manager.commands[command_id].format(str(payload)), 'arousal': arousal, 'valence': valence})



@app.route('/hric/llm/voice', methods=['POST'])
def voice_to_array():
    return (
        RestMaybe(request)
        .wellformed()
        .exists('valence')
        .exists('arousal')
        .exists('b64audio')
        .run(lambda _, request_data: _voice_to_array(request_data))
    )


def _voice_to_array(request_data: VoiceRequest):
    """Converts an audio request into an array of audio responses. Fails after 5 attempts.

    Args:
        request_data (VoiceRequest): The request containing a base64-encoded audio string, valence and arousal
    """
    valence = request_data['valence']
    arousal = request_data['arousal']
    audio = base64.b64decode(request_data['b64audio'])
    text = stt.audio_to_text(audio)
    if text is None:
        response = tts.speak_array(
            [
                SpeechExpression(
                    Emotion.WORRIED,
                    llm.prompt_manager.error_messages['fail_message'],
                )
            ]
        )
        return {
            'diff_arousal': 0,
            'diff_valence': 0,
            'response_messages': _response_array_to_json(response),
        }
    else:
        return _text_to_array({'valence': valence, 'arousal': arousal, 'text': text})


@app.route('/hric/llm/text', methods=['POST'])
def text_to_array():
    return (
        RestMaybe(request)
        .wellformed()
        .exists('valence')
        .exists('arousal')
        .exists('text')
        .run(lambda _, request_data: _text_to_array(request_data))
    )


def _text_to_array(request_data: TextRequest):
    """Converts a text request into an array of audio responses. Fails after 5 attempts.

    Args:
        request_data (TextRequest): The request containing valence, arousal and the text to ask the LLM.
    """
    valence = request_data['valence']
    arousal = request_data['arousal']
    text = request_data['text']
    print(f'Detected request: {text}')
    fail_history = ChatHistory()
    fail_history.chat_as_user(text)
    llm.prompt_manager.set_mood(arousal, valence)
    response = llm.ask(text)
    array = None

    i = 0
    j = 0
    while True:
        if j > 5:
            break
        try:
            parsed = Parser(response).parse(result_analysis=False)
            if isinstance(parsed[0], MoveExpression):
                return {
                    'diff_arousal': 0,
                    'diff_valence': 0,
                    'move': parsed[0].exhibit_key,
                }
            array = tts.speak_array(parsed)
            break
        except ParseException as e:
            print(f'Got ParseException for {response}: {repr(e)}')
            fail_history.chat_as_llm(response, True)
            response = llm.ask_with_history(llm.prompt_manager.error_messages['parser_error'].format(repr(e)), fail_history)
            j = j + 1
        except ResultException as e:
            print(f'Got ResultException for {response}: {repr(e)}')
            fail_history.chat_as_llm(response, True)
            response = llm.ask_with_history(llm.prompt_manager.error_messages['parser_error'].format(repr(e)), fail_history)
            i = i + 1
            j = j + 1
        except Exception as e:
            print(f'Got Exception for {response}: {repr(e)}')
            fail_history.chat_as_llm(response, True)
            response = llm.ask_with_history(llm.prompt_manager.error_messages['parser_error'].format(repr(e)), fail_history)
            j = j + 1
    
    if array is None:
        array = tts.speak_array(
            cast(
                List[Expression],
                [
                    SpeechExpression(
                        emotion=Emotion.FRUSTRATED,
                        text=llm.prompt_manager.error_messages['timeout_message'],
                    )
                ],
            )
        )

    response_array = _response_array_to_json(array)

    answer_text = ''

    for response in response_array:
        if response['text'] != '_pause':
            answer_text += f'{response["text"]} '

    llm.chat_history.add_question_answer(text, answer_text)

    with open(get_resource('test.txt'), 'w') as fd:
        fd.write(str(json.dumps(llm.prompt_manager.prompts, indent=4)))

    return {'diff_arousal': 0, 'diff_valence': 0, 'response_messages': response_array}


def _response_array_to_json(
    array: List[tuple[str, Emotion | None, bytes | None]]
) -> List[dict]:
    out = []
    for text, emotion, bytestream in array:
        if text == '_pause':
            out.append({'emotion': -1, 'text': text, 'b64audio': 'none'})
        else:
            out.append(
                {
                    'emotion': cast(Emotion, emotion).value[0],
                    'text': text,
                    'b64audio': base64.b64encode(cast(bytes, bytestream)).decode(
                        'ascii'
                    ),
                }
            )
    return out


@app.route('/hric/llm/exhibit/list', methods=['PATCH'])
def patch_exhibit_list():
    return (
        RestMaybe(request)
        .wellformed()
        .exists('keys')
        .run(lambda _, request: _patch_exhibit_list(request))
    )


def _patch_exhibit_list(request: UpdateExhibitKeysRequest):
    """Updates the active exhibits for the LLM to consider.

    Args:
        request (UpdateExhibitKeysRequest): The request containing keys for the exhibits to activate.
    """
    keys = request['keys']
    try:
        llm.prompt_manager.update_active_exhibits(keys)
        return {}, 200
    except Exception as e:
        return ({'error': str(e)}, 404)


@app.route('/hric/llm/exhibit/context', methods=['PATCH'])
def patch_exhibit_context():
    return (
        RestMaybe(request)
        .wellformed()
        .exists('exhibit_key')
        .run(lambda _, request: _patch_exhibit_context(request))
    )


def _patch_exhibit_context(request: UpdateExhibitContextRequest):
    """Updates the current exhibit for the LLM.

    Args:
        request (UpdateExhibitContextRequest): The request containing the exhibit key.
    """
    key = request['exhibit_key']
    try:
        llm.prompt_manager.set_exhibit_context(key)
        return {}, 200
    except Exception as e:
        return ({'error': str(e)}, 404)


# For debugging only!! For production, execute the docker container instead.
if __name__ == '__main__':
    print('Starting HTTP Server')
    app.run(host='127.0.0.1', port=int(SERVER_PORT))
