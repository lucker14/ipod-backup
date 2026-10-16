# Homebrew tap for iPod Backup

Install iPod Backup from this tap:

```sh
brew tap lucker14/ipod-backup
brew install ipod-backup
```

The formula downloads a versioned, checksum-verified portable release from
the main [iPod Backup repository](https://github.com/lucker14/ipod-backup).
Python 3.12 is installed as a Homebrew dependency.

To publish a later version, update `Formula/ipod-backup.rb` from the
corresponding versioned formula template and verify its release archive
SHA-256 against the main repository's `SHA256SUMS`.
