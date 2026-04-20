import os
import subprocess
import tempfile


def _run(cmd: list[str]) -> None:
    """Run a shell command, raising RuntimeError with stderr on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}):\n"
            f"{result.stderr[-3000:]}"
        )


def get_duration(video_path: str) -> float:
    """Return video duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{result.stderr[-2000:]}")
    return float(result.stdout.strip())


def concat_segments(
    input_path: str,
    segments: list[dict],
    output_path: str,
) -> str:
    """
    Cut one or more segments from input_path (on exact sentence boundaries)
    and concatenate them into a single output file.
    segments: [{start_ms, end_ms}, ...]
    Returns output_path.
    """
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    if len(segments) == 1:
        seg = segments[0]
        start_s   = seg["start_ms"] / 1000
        duration_s = (seg["end_ms"] - seg["start_ms"]) / 1000
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_s),
            "-i", input_path,
            "-t", str(duration_s),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]
        _run(cmd)
        return output_path

    # Multiple segments: cut each to a temp file, then concat
    tmp_dir   = tempfile.mkdtemp()
    tmp_files = []
    concat_list = os.path.join(tmp_dir, "concat.txt")

    try:
        for i, seg in enumerate(segments):
            tmp_path   = os.path.join(tmp_dir, f"seg_{i}.mp4")
            start_s    = seg["start_ms"] / 1000
            duration_s = (seg["end_ms"] - seg["start_ms"]) / 1000
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_s),
                "-i", input_path,
                "-t", str(duration_s),
                # Re-encode to ensure consistent parameters before concat
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                "-avoid_negative_ts", "make_zero",
                tmp_path,
            ]
            _run(cmd)
            tmp_files.append(tmp_path)

        with open(concat_list, "w") as f:
            for p in tmp_files:
                f.write(f"file '{p}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            output_path,
        ]
        _run(cmd)
    finally:
        for p in tmp_files:
            if os.path.exists(p):
                os.remove(p)
        for f in [concat_list]:
            if os.path.exists(f):
                os.remove(f)
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    return output_path


def burn_overlays(
    input_path: str,
    output_path: str,
    hook_text: str,
    speaker_name: str,
    duration_s: float,
) -> str:
    """
    Burn hook text, speaker lower-third, and Scaler outro CTA onto the clip.
    Uses textfile= instead of text= to avoid FFmpeg quoting issues with
    apostrophes, colons, and other special characters.
    """
    hook_len    = min(4.5, duration_s * 0.25)
    lt_start    = min(1.5, duration_s * 0.1)
    lt_end      = max(lt_start + 1.0, duration_s - 2.5)
    outro_start = max(0.0, duration_s - 2.5)

    tmp_dir = tempfile.mkdtemp()
    hook_file   = os.path.join(tmp_dir, "hook.txt")
    name_file   = os.path.join(tmp_dir, "name.txt")
    label_file  = os.path.join(tmp_dir, "label.txt")
    outro_file  = os.path.join(tmp_dir, "outro.txt")

    try:
        with open(hook_file,  "w", encoding="utf-8") as f:
            f.write(hook_text[:110])
        with open(name_file,  "w", encoding="utf-8") as f:
            f.write(speaker_name[:40])
        with open(label_file, "w", encoding="utf-8") as f:
            f.write("SCALER PODCAST")
        with open(outro_file, "w", encoding="utf-8") as f:
            f.write("Watch the full podcast on Scaler YouTube")

        vf = ",".join([
            # Hook text — dark bar across top
            f"drawbox=x=0:y=0:w=iw:h=72:color=black@0.75:t=fill"
            f":enable='between(t,0,{hook_len:.2f})'",

            f"drawtext=textfile={hook_file}"
            f":fontsize=22:fontcolor=white"
            f":x=(w-text_w)/2:y=18"
            f":shadowcolor=black:shadowx=1:shadowy=1"
            f":enable='between(t,0,{hook_len:.2f})'",

            # Speaker lower-third — dark box bottom-left
            # drawbox uses ih; drawtext uses h for frame height
            f"drawbox=x=8:y=ih-80:w=310:h=66:color=black@0.78:t=fill"
            f":enable='between(t,{lt_start:.2f},{lt_end:.2f})'",

            f"drawtext=textfile={name_file}"
            f":fontsize=17:fontcolor=white"
            f":x=18:y=h-70"
            f":enable='between(t,{lt_start:.2f},{lt_end:.2f})'",

            f"drawtext=textfile={label_file}"
            f":fontsize=11:fontcolor=0xf6c90e"
            f":x=18:y=h-46"
            f":enable='between(t,{lt_start:.2f},{lt_end:.2f})'",

            # Outro CTA — centred dark bar
            f"drawbox=x=iw/2-258:y=ih/2-26:w=516:h=52:color=black@0.82:t=fill"
            f":enable='between(t,{outro_start:.2f},{duration_s:.2f})'",

            f"drawtext=textfile={outro_file}"
            f":fontsize=14:fontcolor=white"
            f":x=(w-text_w)/2:y=(h-text_h)/2"
            f":enable='between(t,{outro_start:.2f},{duration_s:.2f})'",
        ])

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]
        _run(cmd)
    finally:
        for f in [hook_file, name_file, label_file, outro_file]:
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    return output_path
