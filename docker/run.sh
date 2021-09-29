sudo docker run \
--name 'fylm' \
-v /Volumes/Films:/Volumes/Films \
-v /Volumes/Downloads:/Volumes/Downloads \
-v /path/to/docker/fylm:/config \
--rm \
brandonscript/fylm:latest \
"--config" "/config/config.yaml"
"-s" "/Volumes/Downloads" "--plaintext" "--other-args-here"