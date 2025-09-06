#!/usr/bin/env python3
"""
Audio to Text Converter
Converts audio files to text using Google's speech recognition API
"""

import speech_recognition as sr
from pydub import AudioSegment
import os
import sys

def convert_audio_to_wav(audio_file_path):
    """Convert audio file to WAV format if needed"""
    file_extension = os.path.splitext(audio_file_path)[1].lower()
    
    if file_extension == '.wav':
        return audio_file_path
    
    # Convert to WAV
    try:
        audio = AudioSegment.from_file(audio_file_path)
        wav_file_path = os.path.splitext(audio_file_path)[0] + '_converted.wav'
        audio.export(wav_file_path, format="wav")
        print(f"Converted {audio_file_path} to {wav_file_path}")
        return wav_file_path
    except Exception as e:
        print(f"Error converting audio file: {e}")
        return None

def audio_to_text(audio_file_path, language='en-US'):
    """Convert audio file to text"""
    
    # Initialize recognizer
    recognizer = sr.Recognizer()
    
    # Convert to WAV if needed
    wav_file_path = convert_audio_to_wav(audio_file_path)
    if not wav_file_path:
        return None
    
    try:
        # Load audio file
        with sr.AudioFile(wav_file_path) as source:
            print("Loading audio file...")
            audio_data = recognizer.record(source)
        
        # Recognize speech using Google Speech Recognition
        print("Converting speech to text...")
        text = recognizer.recognize_google(audio_data, language=language)
        
        # Clean up converted file if it was created
        if wav_file_path != audio_file_path:
            os.remove(wav_file_path)
        
        return text
    
    except sr.UnknownValueError:
        print("Could not understand the audio")
        return None
    except sr.RequestError as e:
        print(f"Error with speech recognition service: {e}")
        return None
    except Exception as e:
        print(f"Error processing audio: {e}")
        return None

def main():
    """Main function to handle user input and convert audio to text"""
    
    # Get audio file path from user
    if len(sys.argv) > 1:
        audio_file_path = sys.argv[1]
    else:
        audio_file_path = input("Enter the path to your audio file: ").strip()
    
    # Check if file exists
    if not os.path.exists(audio_file_path):
        print(f"Error: File '{audio_file_path}' not found!")
        return
    
    # Get language (optional)
    language = input("Enter language code (default: en-US): ").strip()
    if not language:
        language = 'en-US'
    
    print(f"\nProcessing audio file: {audio_file_path}")
    print("This may take a moment...\n")
    
    # Convert audio to text
    result = audio_to_text(audio_file_path, language)
    
    if result:
        print("=" * 50)
        print("TRANSCRIBED TEXT:")
        print("=" * 50)
        print(result)
        print("=" * 50)
        
        # Ask if user wants to save to file
        save = input("\nSave to text file? (y/n): ").lower().strip()
        if save in ['y', 'yes']:
            output_file = os.path.splitext(audio_file_path)[0] + '_transcript.txt'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"Transcript saved to: {output_file}")
    else:
        print("Failed to convert audio to text.")

if __name__ == "__main__":
    main()