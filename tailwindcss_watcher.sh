#!/bin/sh
eval "$(command conda 'shell.bash' 'hook' 2> /dev/null)"
conda activate evmos
cd ..
tailwindcss -i style.css -o static/tailwind.css