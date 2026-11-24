# usage: standalone.py page.html datadir out.html "Title"
import sys,json,glob,os,csv
page,dd,out,title=sys.argv[1:5]
here=os.path.dirname(os.path.abspath(__file__))
head=open(f'{here}/standalone_head.html').read()
import re
head=re.sub(r'<title>.*?</title>',f'<title>{title} – SF6 review</title>',head)
shim=open(f'{here}/standalone_shim.js').read()
data={os.path.basename(f)[:-5]:json.load(open(f)) for f in glob.glob(dd+'/*.json')}
p=open(page).read().replace('<meta name="dash-one-writer">\n','')
html=head+'<script>\nwindow.__DATA__='+json.dumps(data,ensure_ascii=False)+';\n'+shim+'</script>\n'+p+'\n</body></html>'
open(out,'w').write(html)
# csv copies
os.makedirs(os.path.dirname(out)+'/data',exist_ok=True)
for k,v in data.items():
  json.dump(v,open(f'{os.path.dirname(out)}/data/{k}.json','w'),indent=1,ensure_ascii=False)
  if v:
    keys=list(dict.fromkeys(k2 for r in v for k2 in r))
    w=csv.DictWriter(open(f'{os.path.dirname(out)}/data/{k}.csv','w',newline=''),fieldnames=keys); w.writeheader(); w.writerows(v)
print(out,len(html))
