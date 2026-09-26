# iPod nano music backup (macOS)

This guide covers backing up an iPod nano mounted as a disk, giving tracks
readable filenames, collecting them in one folder, and playing them on shuffle
over AirPlay.

The backup tool is `ipod_backup.py`. It uses only Python's standard library;
there are no packages to install. It copies the iPod's `iPod_Control` contents
without changing the iPod. A completed backup preserves the original folder
structure and includes music files plus library databases and other files.

## TL;DR

Open Terminal. The commands below use the iPod volume name from this example;
replace it if yours differs. Do not type the `$` displayed at the end of a
Terminal prompt.

```sh
python3 /Users/petrpluhar/Documents/Git/ipod-backup/ipod_backup.py backup '/Volumes/IPOD UªÍVAT' "$HOME/Music/iPod-backup"
python3 /Users/petrpluhar/Documents/Git/ipod-backup/ipod_backup.py compare '/Volumes/IPOD UªÍVAT' "$HOME/Music/iPod-backup" --hash
python3 /Users/petrpluhar/Documents/Git/ipod-backup/ipod_backup.py organize "$HOME/Music/iPod-backup"
```

The last command renames tagged audio files in place to `Artist - Title.mp3`
(or just `Title.mp3` if artist information is missing). To collect music into
one folder, create `~/Documents/ipod` and move the audio files from
`~/Music/iPod-backup/Music/F00` through `F13` into it, choosing **Keep Both**
if Finder reports duplicate names. The current collected folder is:

```text
~/Documents/ipod
```

In Music, import that folder, make a playlist from the imported tracks, turn
on Shuffle, and choose the TV from AirPlay.

## Beginner guide

### 1. Find and back up the iPod

1. Connect the iPod and wait for it to appear in Finder.
2. Open Terminal (Finder → Applications → Utilities → Terminal).
3. To see the exact mounted volume name, run:

   ```sh
   ls -1 /Volumes
   ```

   Use the name shown there, including spaces and accents. Put the full path
   inside single quotes, for example `'/Volumes/IPOD UªÍVAT'`. Do not include
   the `$` at the end of the Terminal prompt; that is just the prompt marker.
4. Run the backup command below, substituting the mounted volume path if it
   differs:

   ```sh
   python3 /Users/petrpluhar/Documents/Git/ipod-backup/ipod_backup.py backup '/Volumes/IPOD UªÍVAT' "$HOME/Music/iPod-backup"
   ```

   `$HOME` means your home folder. The destination is
   `~/Music/iPod-backup`. The first copy may take a while. Each file is copied
   through a temporary file and locally verified before it is put in place.
   The script retries reads three times by default. If a connection/read error
   remains, reconnect the iPod and run the same command again to resume.
5. While the iPod is still connected, verify the backup:

   ```sh
   python3 /Users/petrpluhar/Documents/Git/ipod-backup/ipod_backup.py compare '/Volumes/IPOD UªÍVAT' "$HOME/Music/iPod-backup" --hash
   ```

   Hash comparison reads every file on both devices and can take time. `MISSING`
   or `DIFFERS` entries need attention; `EXTRA` entries are in the backup but
   not on the iPod. The tool never deletes destination files. Do this check
   before moving tracks out of their backup folders.

### 2. Rename tracks from their tags

The music is usually under `~/Music/iPod-backup/Music/F00`, `F01`, and similar
folders. The iPod gave files opaque names; their artist and title are often
embedded in each audio file.

Run:

```sh
python3 /Users/petrpluhar/Documents/Git/ipod-backup/ipod_backup.py organize "$HOME/Music/iPod-backup"
```

The organizer reads embedded ID3 tags in MP3 files and common metadata tags in
M4A/MP4-family files. It renames tagged tracks to `Artist - Title.ext`, or
`Title.ext` without an artist. It preserves the directories and extensions,
adds a numbered suffix when names conflict, and leaves files without readable
tags untouched. It does not read the iPod's `iTunesDB` as a fallback and does
not rename anything on the iPod.

The command continues past individual errors and retries each rename three
times. Fix any reported problem and rerun the same command to continue. A
hidden `.ipod-backup-names.json` map lets the backup and compare commands track
renamed files as long as the files remain in their original `Fxx` folders.

### 3. Collect songs in one folder (optional)

Keeping the `Fxx` folders is best if you want to retain a directly comparable
backup. For a separate, flat folder for playback:

1. In Finder, choose **Go → Go to Folder…** and enter:

   ```text
   ~/Music/iPod-backup/Music
   ```

2. Create `~/Documents/ipod` if it does not exist.
3. Open each `F00` through `F13` folder, select the audio files, and move them
   into `~/Documents/ipod`. If Finder warns that a filename already exists,
   choose **Keep Both** so neither copy is lost. macOS will add a suffix to
   distinguish duplicate names.
4. Ignore hidden `._*` AppleDouble sidecar files; they are not songs.

The moved files no longer live in the backup's original `Fxx` locations. The
name map records their old paths, so a comparison or resumed backup will not
find them at those locations. Keep the iPod connected and run `backup` again
if you need to restore the original, verifiable backup layout; that will copy
the songs back under `Fxx` and leave the listening copies in `~/Documents/ipod`.

### 4. Set file permissions (usually unnecessary)

The collected files were set to mode `777` in this example. That gives every
local user and process permission to read, modify, and execute each file.
MP3s do not need execute permission, and broad write access is generally not
recommended. For a personal music folder, `644` on files is a safer default:

```sh
find "$HOME/Documents/ipod" -type f -exec chmod 644 {} +
```

If you specifically need the earlier `777` permissions, use:

```sh
find "$HOME/Documents/ipod" -type f -exec chmod 777 {} +
```

### 5. Shuffle playback through AirPlay

The built-in Music app supports both shuffle and AirPlay:

1. Open Music.
2. Choose **File → Add to Library…** and select `~/Documents/ipod`.
3. Select the imported tracks and choose **File → New Playlist from
   Selection**.
4. Open that playlist and click the Shuffle control (crossed arrows).
5. Click the AirPlay control and select the TV or Apple TV.

If the TV is not listed, make sure it supports AirPlay and is on the same
network as the Mac. You can also choose it from Control Center's **Screen
Mirroring** or **Sound** controls, depending on the macOS version.

## Commands and troubleshooting

List mounted volumes:

```sh
ls -1 /Volumes
```

Compare by file size (faster, but does not detect same-size content changes):

```sh
python3 /Users/petrpluhar/Documents/Git/ipod-backup/ipod_backup.py compare '/Volumes/IPOD UªÍVAT' "$HOME/Music/iPod-backup"
```

Compare by SHA-256 (thorough, but slower):

```sh
python3 /Users/petrpluhar/Documents/Git/ipod-backup/ipod_backup.py compare '/Volumes/IPOD UªÍVAT' "$HOME/Music/iPod-backup" --hash
```

If a volume path ending in `$` does not exist, the script retries once without
that final character. It keeps the `$` if the full path really exists.

Run the test suite from this repository directory:

```sh
python3 -m unittest -v
```
