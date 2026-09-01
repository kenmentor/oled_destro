"""
OLED-DESTRO Sidecar Entry Point

This is the main entry point for the Tauri Python sidecar.
It communicates with the Tauri app via a JSON protocol over stdin/stdout.

PROTOCOL:
  Input (stdin):  {"command": "convert", "pdf_path": "C:\\path\\to\\file.pdf", "output_dir": "C:\\path\\to\\output", "voice": "af_heart"}
  Output (stdout): {"type": "status", "message": "extracting text..."}
                   {"type": "status", "message": "synthesizing chunk 1/5..."}
                   {"type": "progress", "percent": 45}
                   {"type": "done", "audio_path": "C:\\path\\to\\output.wav"}
                   {"type": "error", "message": "description of error"}

All communication is one JSON object per line, newline-delimited.
Never use print() for anything other than JSON output on stdout.
Use sys.stderr for debug logging.
"""

import sys
import os
import json
import traceback

# Path resolution for PyInstaller --onefile
if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# Add base dir to Python path so modules/ is discoverable
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from modules import ttsEgine, documentToText


def get_resource_path(relative_path):
    """
    Resolve the absolute path to a bundled resource.

    When frozen with PyInstaller --onefile, resources are extracted to a
    temporary _MEI directory. sys._MEIPASS points to that directory.
    When running as a script, resources live in `modules/`.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", base_dir)
        return os.path.join(meipass, relative_path)
    return os.path.join(base_dir, "modules", relative_path)


def write_output(obj):
    """Write a JSON object to stdout as a single line, then flush."""
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()


def write_status(message):
    write_output({"type": "status", "message": message})


def write_progress(percent):
    write_output({"type": "progress", "percent": int(percent)})


def write_done(audio_path):
    write_output({"type": "done", "audio_path": audio_path})


def write_error(message):
    write_output({"type": "error", "message": message})


def handle_convert(command_data):
    """
    Main conversion handler.

    Expected command_data keys:
      - pdf_path:    Absolute path to the PDF file
      - output_dir:  Directory to write the output WAV (optional, defaults to pdf_dir)
      - voice:       Voice model name without .pt extension (optional, default "af_heart")
    """
    pdf_path = command_data.get("pdf_path", "")
    output_dir = command_data.get("output_dir", "")
    voice_name = command_data.get("voice", "af_heart")

    # Validate PDF path
    if not pdf_path:
        write_error("No pdf_path provided")
        return

    if not os.path.exists(pdf_path):
        write_error(f"PDF file not found: {pdf_path}")
        return

    # Resolve output directory
    if not output_dir:
        output_dir = os.path.dirname(pdf_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Resolve resource paths for TTS engine
    config_path = get_resource_path("config.json")
    model_path = get_resource_path("kokoro-v1_0.pth")
    voice_path = get_resource_path(os.path.join("voices", f"{voice_name}.pt"))

    # Verify required resources exist
    for rpath, rname in [
        (config_path, "config.json"),
        (model_path, "kokoro-v1_0.pth"),
        (voice_path, f"voices/{voice_name}.pt"),
    ]:
        if not os.path.exists(rpath):
            write_error(f"Required resource not found: {rname} at {rpath}")
            return

    try:
        # Initialize document parser
        write_status("Initializing document parser...")
        doc_processor = documentToText.DocumentToText()

        # Extract text from PDF
        write_status(f"Extracting text from: {os.path.basename(pdf_path)}")
        doc_processor.process_document(pdf_path, document_type="pdf")

        # Initialize TTS engine with resolved paths
        write_status("Loading TTS model (this may take a moment)...")
        tts_engine = ttsEgine.TTSEngine(
            config_path=config_path,
            model_path=model_path,
            voice_path=voice_path,
        )

        # Determine output filename
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        output_filename = f"{pdf_basename}.wav"
        output_path = os.path.join(output_dir, output_filename)

        # Process chunks and synthesize
        chunks = list(doc_processor.get_all_chunks())
        total_chunks = len(chunks)

        if total_chunks == 0:
            write_error("No text extracted from the PDF")
            return

        write_status(f"Found {total_chunks} chunk(s) to synthesize")

        # Reset TTS engine for this job
        tts_engine.reset_for_job(output_path)

        for idx, chunk_text in enumerate(chunks):
            chunk_num = idx + 1
            percent = int((idx / total_chunks) * 100)
            write_status(f"Synthesizing chunk {chunk_num}/{total_chunks}...")
            write_progress(percent)

            # Synthesize and write to disk (engine handles WAV assembly)
            list(tts_engine.synthesize(chunk_text))

            write_progress(int((chunk_num / total_chunks) * 100))

        # Ensure final WAV header is written
        tts_engine.finalize_wav()

        write_status("Conversion complete!")
        write_done(output_path)

    except Exception as e:
        # Send full traceback to stderr for debugging
        print(traceback.format_exc(), file=sys.stderr)
        write_error(f"Conversion failed: {str(e)}")


def main():
    """
    Main loop: read JSON commands from stdin, dispatch to handlers.
    """
    write_status("OLED-DESTRO sidecar ready")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            command_data = json.loads(line)
        except json.JSONDecodeError as e:
            write_error(f"Invalid JSON input: {str(e)}")
            continue

        command = command_data.get("command", "")

        if command == "convert":
            handle_convert(command_data)
        elif command == "ping":
            write_output({"type": "pong"})
        elif command == "exit":
            write_status("Shutting down")
            break
        else:
            write_error(f"Unknown command: {command}")


if __name__ == "__main__":
    print("hellllllll")
    main()
