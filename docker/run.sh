sudo docker run \
--name 'fylm' \
-v /volume1/Films:/volume1/Films \
-v /volume1/Downloads:/volume1/Downloads \
-v /volume1/docker/fylm:/config \
--rm \
brandonscript/fylm:latest \
"--config" "/config/config.yaml"
"-s" "/volume1/Downloads/#done/#usenet" "--plaintext"