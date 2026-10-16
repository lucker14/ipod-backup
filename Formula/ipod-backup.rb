class IpodBackup < Formula
  desc "Back up files from an iPod mounted as a disk"
  homepage "https://github.com/lucker14/ipod-backup"
  license "MIT"
  head "https://github.com/lucker14/ipod-backup.git", branch: "main"

  depends_on "python@3.12"

  def install
    libexec.install "ipod_backup.py", "device_test.py", "start_backup.py"
    doc.install "LICENSE"

    {
      "ipod-backup"      => "start_backup.py",
      "ipod-backup-cli"  => "ipod_backup.py",
      "ipod-backup-test" => "device_test.py",
    }.each do |command, script|
      (bin/command).write <<~SH
        #!/bin/sh
        exec "#{formula_opt_bin("python@3.12")}/python3" "#{libexec}/#{script}" "$@"
      SH
      (bin/command).chmod 0755
    end
  end

  test do
    assert_match "usage:", shell_output("#{bin}/ipod-backup-cli --help")
  end
end
