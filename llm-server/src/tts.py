import os
from io import BytesIO
from typing import List, Literal, Optional
import torch
import soundfile
from openvoice import se_extractor
from openvoice.api import BaseSpeakerTTS, ToneColorConverter
from melo.api import TTS
from faster_whisper import WhisperModel
from parsing.token import Emotion
from parsing.expression import *
from pathlib import Path
from util import get_resource

DEFAULT_EN_SPEAKER_EMOTION_MAP = {
    Emotion.AMUSED: ('cheerful', 1.0),
    Emotion.BORED: ('sad', 0.8),
    Emotion.CALM: ('default', 1.0),
    Emotion.EXCITED: ('cheerful', 1.1),
    Emotion.FRUSTRATED: ('angry', 1.0),
    Emotion.HAPPY: ('friendly', 1.0),
    Emotion.SAD: ('sad', 0.9),
    Emotion.WORRIED: ('terrified', 0.8),
}

THORSTEN_DE_SPEAKER_EMOTION_MAP = {
    Emotion.AMUSED: ('DE-amused', 1.0),
    Emotion.BORED: ('DE-sleepy', 1.0),
    Emotion.CALM: ('DE-neutral', 1.0),
    Emotion.EXCITED: ('DE-amused', 1.2),
    Emotion.FRUSTRATED: ('DE-angry', 0.9),
    Emotion.HAPPY: ('DE-amused', 1.1),
    Emotion.SAD: ('DE-sleepy', 0.8),
    Emotion.WORRIED: ('DE-surprised', 1.1),
}


class TTSWrapper:

    def __init__(
        self,
        reference_speaker: str,
        base_speaker: str = get_resource('tts/checkpoints/v1/base_speakers/EN'),
        language: str = '',
        openvoice_version: Literal[1, 2, 'melo'] = 1,
        fp16_available: bool = True,
        speaker_map: dict[Emotion, tuple[str, float]] | None = None,
    ):
        if speaker_map is None:
            speaker_map = DEFAULT_EN_SPEAKER_EMOTION_MAP

        if openvoice_version == 'melo':
            self.checkpoint_dir = get_resource('tts/checkpoints/v2')
        else:
            self.checkpoint_dir = get_resource(f'tts/checkpoints/v{openvoice_version}')

        self.converter = f'{self.checkpoint_dir}/converter'
        self.device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        self.speaker_map = speaker_map

        if base_speaker.endswith('/'):
            base_speaker = base_speaker[0 : (len(base_speaker) - 1)]

        match openvoice_version:
            case 1:
                self.tts = BaseSpeakerTTS(
                    f'{base_speaker}/config.json', device=self.device
                )
                self.tts.load_ckpt(f'{base_speaker}/checkpoint.pth')
                self.source_se = torch.load(
                    f'{self.checkpoint_dir}/base_speakers/EN/en_style_se.pth'
                ).to(self.device)
            case 2:
                # ...
                pass
            case 'melo':
                self.tts = TTS(
                    language=language,
                    config_path=f'{base_speaker}/config.json',
                    ckpt_path=f'{base_speaker}/checkpoint.pth',
                )
                self.source_se = torch.load(
                    f'{self.checkpoint_dir}/base_speakers/ses/en-us.pth'
                ).to(self.device)

        self.tone_color_converter = ToneColorConverter(f'{self.converter}/config.json')

        cpu_cores = os.cpu_count()

        se_extractor.model = WhisperModel(
            'tiny.en',
            cpu_threads=4 if cpu_cores is None else cpu_cores,
            device='cuda' if torch.cuda.is_available() else 'cpu',
            compute_type='default' if fp16_available else 'Float32',
        )
        self.tone_color_converter.load_ckpt(f'{self.converter}/checkpoint.pth')

        self.target_se, self.audio_name = se_extractor.get_se(
            reference_speaker,
            self.tone_color_converter,
            target_dir='processed',
            vad=True,
        )

    def speak(
        self,
        emotion: Emotion,
        text: str,
        tone_colored: bool = True,
    ) -> bytes:
        speaker, speed = self.speaker_map[emotion]
        if isinstance(self.tts, BaseSpeakerTTS):
            self.tts = cast(BaseSpeakerTTS, self.tts)
            audio = self.tts.tts(text, None, speaker, speed=speed)
        else:
            self.tts = cast(TTS, self.tts)
            speaker_id = self.tts.hps.data.spk2id[speaker]
            audio = self.tts.tts_to_file(text, speaker_id, None, speed)
        file_object = BytesIO()
        soundfile.write(
            file_object, audio, self.tts.hps.data.sampling_rate, format='WAV'
        )
        file_object.seek(0)
        if tone_colored:
            encode_message = '@MyShell'
            tone_colored_audio = self.tone_color_converter.convert(
                audio_src_path=soundfile.SoundFile(file_object),
                src_se=self.source_se,
                tgt_se=self.target_se,
                output_path=None,
                message=encode_message,
            )
            file_object.seek(0)
            file_object.truncate(0)
            soundfile.write(
                file_object,
                tone_colored_audio,
                self.tts.hps.data.sampling_rate,
                format='WAV',
            )
        return file_object.getvalue()

    def speak_array(self, expressions: "list[Expression]", tone_colored: bool = False):
        out_array: List[tuple[str, Optional[Emotion], Optional[bytes]]] = []
        for expression in expressions:
            if isinstance(expression, SpeechExpression):
                data = self.speak(expression.emotion, expression.text, tone_colored)
                out_array.append((expression.text, expression.emotion, data))
            elif isinstance(expression, PauseExpression):
                out_array.append(('_pause', None, None))

        return out_array

    def speak_to_file(
        self,
        file_name: str,
        emotion: Emotion,
        text: str,
        tone_colored: bool = True,
    ) -> str:
        data = self.speak(emotion, text, tone_colored)
        with open(file_name, 'wb') as fd:
            fd.write(data)

        return file_name

    @staticmethod
    def get_openvoice(
        base_speaker: str,
        reference_speaker: str,
        openvoice_version: Literal[1, 2] = 2,
        fp16_available: bool = True,
    ):
        return TTSWrapper(
            base_speaker, reference_speaker, '', openvoice_version, fp16_available
        )

    @staticmethod
    def get_melo(
        reference_speaker: str,
        base_speaker: str,
        language: str,
        fp16_available: bool = True,
        speaker_map: dict[Emotion, tuple[str, float]] = DEFAULT_EN_SPEAKER_EMOTION_MAP,
    ):
        return TTSWrapper(
            reference_speaker,
            base_speaker,
            language,
            'melo',
            fp16_available,
            speaker_map,
        )
