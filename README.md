Home Assistant setup for PyCharm and python 3.13:

```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.13-full python3.13-dev
python3.13 --version
python3.13 -m ensurepip --upgrade
python3.13 -m pip install --upgrade pip

sudo apt-get update
sudo apt-get install python3-pip python3-dev python3-venv autoconf libssl-dev libxml2-dev
libxslt1-dev libjpeg-dev libffi-dev libudev-dev zlib1g-dev pkg-config libavformat-dev
libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libswresample-dev
libavfilter-dev ffmpeg libgammu-dev build-essential libturbojpeg


mkdir HA
cd HA
git clone https://github.com/Pshatsillo/core.git
cd core
git remote add upstream https://github.com/home-assistant/core.git

sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.12 2
sudo update-alternatives --install /usr/bin/python3 python /usr/bin/python3.12 2

sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.13 2
sudo update-alternatives --install /usr/bin/python3 python /usr/bin/python3.13 2

sudo update-alternatives --config python3
sudo update-alternatives --config python

script/setup
source venv/bin/activate

cd venv/bin
ln -sfT /usr/bin/python3.13 python3

hass -c config

```

run Pycharm, open core, index

set python back to 3.12 or 3.10
```
sudo update-alternatives --config python3
sudo update-alternatives --config python
```
setup config:

script: venv/bin/hass
param: -c config
