cp ../mads mads -r

python3 -c "from mads.const import VERSION;f = open('VERSION', 'w');f.write(str(VERSION))"

pyinstaller mads.spec --workpath build --distpath dist

mkdir -p ../dist;

zip -r "../dist/mads_linux_x64_$(cat VERSION).zip" dist/mads

rm mads -rf
rm build -rf
rm dist -rf
rm VERSION
