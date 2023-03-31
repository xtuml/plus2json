# Regression test plus2json

tc=t01
python ../plus2json/__main__.py t01_straight.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t02
python ../plus2json/__main__.py t02_fork.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t03
python ../plus2json/__main__.py t03_split.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t04
python ../plus2json/__main__.py t04_if.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t05
python ../plus2json/__main__.py t05_switch.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t06
python ../plus2json/__main__.py t06_mixed.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t07
python ../plus2json/__main__.py t07_mixed2.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t08
python ../plus2json/__main__.py t08_unhappy1.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
tc=t09
python ../plus2json/__main__.py t09_unhappy2.puml -p -j > /tmp/o.txt && diff -q /tmp/o.txt $tc-j-p.txt && echo "$tc passed" || echo "$tc failed"
