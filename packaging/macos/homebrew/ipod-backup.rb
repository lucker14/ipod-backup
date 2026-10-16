class IpodBackup < Formula
  desc "Back up files from an iPod mounted as a disk"
  homepage "https://github.com/lucker14/ipod-backup"
  license "MIT"
  head "https://github.com/lucker14/ipod-backup.git", branch: "main"

  depends_on "python@3.12"

  def install
    libexec.install "src/ipod_backup"
    doc.install "LICENSE"

    {
      "ipod-backup"      => "ipod_backup.interactive",
      "ipod-backup-cli"  => "ipod_backup",
      "ipod-backup-test" => "ipod_backup.device_test",
    }.each do |command, module_name|
      (bin/command).write <<~SH
        #!/bin/sh
        export PYTHONPATH="#{libexec}${PYTHONPATH:+:$PYTHONPATH}"
        exec "#{formula_opt_bin("python@3.12")}/python3" -m #{module_name} "$@"
      SH
      (bin/command).chmod 0755
    end
  end

  test do
    assert_match "usage:", shell_output("#{bin}/ipod-backup-cli --help")
  end
end
