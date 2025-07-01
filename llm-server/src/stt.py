import whisper
import os
import numpy as np
import subprocess


class STT:

    def __init__(self, audio_input_folder: str, model: str):
        """Initializes the Speech To Text, loading the desired whisper model.

        Args:
            audio_input_folder (str): The Folder where audio files are put into and can be read from.
            model (str): The desired Whisper model. [More info here](https://github.com/openai/whisper/tree/main?tab=readme-ov-file#available-models-and-languages).
        """
        self.audio_input_folder = audio_input_folder
        self.model = whisper.load_model(model)

    def audio_to_text(self, file: str | bytes) -> str | None:
        """Converts audio into text.

        Args:
            file (str | bytes): The Audio file to be converted into text. Can be a file, can also be a direct bytestream.

        Returns:
            text (str): The text the audio file contained, if whisper could recognize the audio file.
            none (None): Nothing, if whisper did not recognize what the speaker just said.
        """
        if isinstance(file, bytes):
            # For this case, we need to convert the bytestream into a suitable input for whisper first. Then, we can transcribe.
            cmd = [
                'ffmpeg',
                '-threads',
                '0',
                '-i',
                'pipe:0',
                '-f',
                's16le',
                '-ac',
                '1',
                '-acodec',
                'pcm_s16le',
                '-ar',
                str(whisper.audio.SAMPLE_RATE),
                'pipe:1',
            ]
            try:
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE
                )
                out = process.communicate(input=file)[0]
                buffer = np.frombuffer(out, np.int16).astype(np.float32) / 32768.0
                result = self.model.transcribe(buffer)
                txt = result['text']
                return txt if isinstance(txt, str) else None
            except subprocess.CalledProcessError as e:
                print(f'Failed to load audio: {e.stderr.decode()}')
                return None

        elif isinstance(file, str):
            path = f'{self.audio_input_folder}/{file}'
            assert os.path.isfile(path), f'Invalid audio path: {path}'
            result = self.model.transcribe(path)
            txt = result['text']
            return txt if isinstance(txt, str) else None
        else:
            raise Exception('Invalid Type!')
