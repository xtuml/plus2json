# Regression test plus2json

tc=t01
python ../src/__main__.py t01_straight.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t02
python ../src/__main__.py t02_fork.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t03
python ../src/__main__.py t03_split.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t04
python ../src/__main__.py t04_if.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t05
python ../src/__main__.py t05_switch.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t06
python ../src/__main__.py t06_mixed.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t07
python ../src/__main__.py t07_mixed2.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
