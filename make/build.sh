
arch="x64"
os="linux"
pythoncommand="python3"

if [ "$2" == "" ]; then
  echo "warning: argument <architecture> missing, default to x64"
else
  arch="$2"
fi

if [ "$3" == "" ]; then
  echo "warning: argument <operating sys> missing, default to linux"
else
  os="$3"
fi

if [ "$1" == "" ]; then
  echo "warning: argument <python command> missing, default to python3"
else
  pythoncommand="$1"
fi

cp ../mads mads -r

$pythoncommand -c "from mads.const import VERSION;f = open('VERSION', 'w');f.write(str(VERSION))"
version="$(cat VERSION)"

pyinstaller mads.spec --workpath build --distpath dist

mkdir -p ../dist;

echo "$os"
echo "$arch"

cd "dist/mads"

zip -r "../../../dist/mads_${os}_${arch}_${version}.zip" *

cd "../.."

zip -r "../dist/mads_source_${version}.zip" mads/*.py -j

rm mads -rf
rm build -rf
rm dist -rf
rm VERSION
