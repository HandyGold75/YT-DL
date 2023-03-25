from argparse import ArgumentParser
from pytube import YouTube
from pytube.exceptions import VideoUnavailable, VideoRegionBlocked, VideoPrivate
from os import path as osPath, get_terminal_size, remove
from sys import platform
import subprocess
import ffmpeg


class glb:
    if platform == "win32":
        from win32com.shell import shell, shellcon # type: ignore
        workFolder = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, 0, 0)
    else:
        workFolder = osPath.expanduser("~")

    ffmpegLocation = ""

    url = ""
    quality = "medium"
    format = None
    audioOnly = False

    totalSize = 0
    remainingSize = 0


class log:
    totalActions = 0
    actions = 0
    actionsDone = 0

    def progressBar(message: str):
        try:
            cliWidth = get_terminal_size().columns
        except OSError:
            cliWidth = 64

        width = int(cliWidth / 4)

        percent = width * ((log.actions) / log.totalActions)
        bar = chr(9608) * int(percent) + "-" * (width - int(percent))

        if cliWidth <= 40:
            message = ""
        else:
            if len(message) > width:
                message = message[:width] + "..."
            message = message + (" " * (int(cliWidth / 2) - len(message)))

        try:
            print(f"|{bar}| {(100/width)*percent:.2f}% " + message, end="\r")
        except UnicodeEncodeError:
            print(f"|{bar.replace(chr(9608), '#')}| {(100/width)*percent:.2f}% " + message, end="\r")


class setup:
    def arg():
        parser = ArgumentParser(description="Download YouTube videos based on the URL.")
        parser.add_argument("url", default=[], metavar="Target", nargs="*", help="Specify script to run.")
        parser.add_argument("-mp", "-mp4", action="store_true", help="Force mp4 format.")
        parser.add_argument("-au", "-audio", action="store_true", help="Download only audio.")
        parser.add_argument("-lo", "-low", action="store_true", help="Try to download the lowest quality.")
        parser.add_argument("-me", "-medium", action="store_true", help="Try to download a balanced quality video (Default).")
        parser.add_argument("-hi", "-high", action="store_true", help="Try to download the highest quality video.")
        args = parser.parse_args()

        if args.lo + args.me + args.hi > 1:
            parser.parse_args(["-h"])

        if args.url == []:
            glb.url = str(input("URL: "))
        else:
            glb.url = args.url[0]

        glb.audioOnly = args.au

        if args.mp:
            glb.format = "mp4"

        if args.lo:
            glb.quality = "low"
        elif args.me:
            glb.quality = "medium"
        elif args.hi:
            glb.quality = "high"

    def getFFMPEG():
        try:
            subprocess.check_output("ffmpeg -h", stderr=subprocess.STDOUT)
            glb.ffmpegLocation = "ffmpeg"
            return None
        except OSError:
            pass

        if osPath.exists(f'{osPath.split(__file__)[0]}/ffmpeg.exe'):
            glb.ffmpegLocation = f'{osPath.split(__file__)[0]}/ffmpeg.exe'
            return None

        raise FileNotFoundError(f'Make ffmpeg.exe available in PATH or in "{osPath.split(__file__)[0]}"')

    def main():
        setup.arg()
        setup.getFFMPEG()


class youtube:
    def download():
        def onProgress(stream, data, remainingSize):
            log.actions = log.actionsDone + (stream.filesize - remainingSize)
            log.progressBar(f'({log.totalActions / 1048576:.2f} MB)')

        def onComplete(stream, file):
            log.actionsDone = log.actions

        yt = YouTube(glb.url, on_progress_callback=onProgress, on_complete_callback=onComplete)

        try:
            yt.check_availability()
        except (VideoUnavailable, VideoRegionBlocked, VideoPrivate) as err:
            print(f'ERROR: {err}!')
            exit(0)

        selectedAudio = None
        for stream in yt.streams.filter(file_extension=glb.format, only_audio=True, only_video=False):
            if selectedAudio is None:
                selectedAudio = stream

            if glb.quality == "low" and int(stream.abr.replace("kbps", "")) < int(selectedAudio.abr.replace("kbps", "")):
                selectedAudio = stream

            elif glb.quality == "medium" and stream.abr == "128kbps":
                selectedAudio = stream
                break

            elif glb.quality == "high" and int(stream.abr.replace("kbps", "")) > int(selectedAudio.abr.replace("kbps", "")):
                selectedAudio = stream

        if glb.audioOnly:
            log.totalActions += selectedAudio.filesize
            fileAudio = selectedAudio.download(glb.workFolder, f'{selectedAudio.title.replace("|", "")}.{selectedAudio.mime_type.split("/")[-1]}', skip_existing=False)

            return fileAudio, None, selectedAudio, None

        selectedVideo = None
        for stream in yt.streams.filter(file_extension=glb.format, only_audio=False, only_video=True):
            if selectedVideo is None:
                selectedVideo = stream

            if glb.quality == "low" and int(stream.resolution.replace("p", "")) < int(selectedVideo.resolution.replace("p", "")):
                selectedVideo = stream

            elif glb.quality == "medium" and stream.resolution == "1080p":
                selectedVideo = stream
                break

            elif glb.quality == "high" and int(stream.resolution.replace("p", "")) > int(selectedVideo.resolution.replace("p", "")):
                selectedVideo = stream

        log.totalActions += selectedAudio.filesize
        log.totalActions += selectedVideo.filesize

        fileAudio = selectedAudio.download(glb.workFolder, f'{selectedAudio.title.replace("|", "")}.{selectedAudio.mime_type.split("/")[-1]}.audio.tmp', skip_existing=False)
        fileVideo = selectedVideo.download(glb.workFolder, f'{selectedVideo.title.replace("|", "")}.{selectedVideo.mime_type.split("/")[-1]}.video.tmp', skip_existing=False)

        return fileAudio, fileVideo, selectedAudio, selectedVideo

    def main():
        fileAudio, fileVideo, detailsAudio, detailsVideo = youtube.download()

        if glb.audioOnly:
            print(f'\nFinished downloading!\nFile: {fileAudio.replace(".audio.tmp", "")}\nEncoding Audio: {detailsAudio}')
            exit(0)

        ffmpeg.concat(ffmpeg.input(fileVideo), ffmpeg.input(fileAudio), v=1, a=1).output(fileVideo.replace(".video.tmp", "")).overwrite_output().run(cmd=glb.ffmpegLocation)

        remove(fileAudio)
        remove(fileVideo)

        print(f'\nFinished downloading and merging!\nFile: {fileVideo.replace(".video.tmp", "")}\nEncoding Video: {detailsVideo}\nEncoding Audio: {detailsAudio}')


if __name__ == "__main__":
    setup.main()
    youtube.main()