sudo apt update
sudo apt upgrade -y
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install -y python3.12 
sudo apt install -y python3.12-venv 
sudo apt install -y python3.12-dev
sudo apt install -y libmysqlclient-dev
sudo apt install -y jq
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
python3.12 --version
python3.12 -m pip --version
echo "finished installing python3.12"