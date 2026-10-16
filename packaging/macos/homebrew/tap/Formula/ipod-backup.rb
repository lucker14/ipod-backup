class IpodBackup < Formula
  desc "Back up files from an iPod mounted as a disk"
  homepage "https://github.com/lucker14/ipod-backup"
  url "https://github.com/lucker14/ipod-backup/releases/download/v0.1.2/ipod-backup-portable.tar.gz"
  version "0.1.2"
  sha256 "d6418c2dd8fdfe928652bab8a9bd6dfbad975b84f1f3ce512beb9609d28c8c48"
  license "MIT"

  depends_on "python@3.12"

  def install
    libexec.install "ipod-backup"
    doc.install libexec/"ipod-backup/LICENSE"

    {
      "ipod-backup"      => "ipod_backup.interactive",
      "ipod-backup-cli"  => "ipod_backup",
      "ipod-backup-test" => "ipod_backup.device_test",
    }.each do |command, module_name|
      (bin/command).write <<~SH
        #!/bin/sh
        export PYTHONPATH="#{libexec}/ipod-backup${PYTHONPATH:+:$PYTHONPATH}"
        exec "#{formula_opt_bin("python@3.12")}/python3" -m #{module_name} "$@"
      SH
      (bin/command).chmod 0755
    end
  end

  test do
    assert_match "usage:", shell_output("#{bin}/ipod-backup-cli --help")
  end
end
