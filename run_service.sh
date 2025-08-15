

if [ ! -f "/etc/systemd/system/youtube.service" ]; then
    cp youtube.service /etc/systemd/system/youtube.service
fi

# jika file ga berubah skip
if [ $(md5sum youtube.service | awk '{print $1}') = $(md5sum /etc/systemd/system/youtube.service | awk '{print $1}') ]; then
    echo "file youtube.service sudah di copy"
else
    echo "file youtube.service ga berubah"
    cp youtube.service /etc/systemd/system/youtube.service
fi

systemctl daemon-reload
# periksa apakah sudah diaktifkan atau tidak
if [ $(systemctl is-enabled youtube.service) = "disabled" ]; then
    systemctl enable youtube.service
fi

# periksa apakah sudah berjalan atau tidak selain itu reload
if [ $(systemctl is-active youtube.service) = "inactive" ]; then
    systemctl start youtube.service
    systemctl status youtube.service
else
    systemctl restart youtube.service
    systemctl status youtube.service
fi