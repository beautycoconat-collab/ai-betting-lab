"""Generate source inventory, role documentation and immutable baseline comparison."""
import argparse,ast,hashlib,json,zipfile
from pathlib import Path
from foundation.roles import registry

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1];out=root/'reports/phase0';out.mkdir(parents=True,exist_ok=True)
    baseline=Path(a.baseline);records=[]
    with zipfile.ZipFile(baseline) as z:
        for item in z.infolist():
            if item.is_dir():continue
            path=Path(item.filename).relative_to('ai-betting-lab');old=z.read(item);current=root/path
            records.append({'file':str(path),'sha256':hashlib.sha256(old).hexdigest(),'unchanged':current.exists() and current.read_bytes()==old})
    if not all(r['unchanged'] for r in records):raise ValueError('baseline_files_changed')
    (out/'baseline-integrity.json').write_text(json.dumps({'baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'files':records,'all_unchanged':True},indent=2))
    inventory=[]
    for folder in ('betting_lab','engine','foundation'):
        for file in sorted((root/folder).rglob('*.py')):
            tree=ast.parse(file.read_text());imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(n.name for n in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append('.'*node.level+(node.module or ''))
            inventory.append({'file':str(file.relative_to(root)),'description':ast.get_docstring(tree),'imports':sorted(set(imports))})
    (out/'module-inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2))
    lines=['# 14 uzman rol — görev, sözleşme ve yetki kaydı','', 'Bu kayıt hedef mimariyi tanımlar. 14 rol, 14 LLM veya 14 tamamlanmış araştırma servisi değildir. Her rol Python/deterministik iş akışıyla yürütülebilir. LLM zorunlu değildir. Uygulama durumu her rolün altında belirtilmiştir.','']
    for r in registry():
        lines += [f"## {r['ordinal']:02d}. {r['name']} — Motor {r['engine']}",'',f"Kimlik: `{r['id']}`. PostgreSQL grup rolü: `lab_{r['id']}` (NOLOGIN).",'',f"Girdi: {r['inputs']}.",'',f"Çıktı: {r['outputs']}.",'',f"Yetki sınırı: {r['authority']}.",'',f"Aşama 0 durumu: {r['implemented']}.",'']
    lines += ['## Ortak kurallar','', 'Her çalıştırma ayrı agent_run_id ile kaydedilir. Sözleşmeler schema_version=1.0 kullanır. Kaynak, kanıt, model, fixture ve zaman ilişkileri ayrıca doğrulanır. Red Team ve Hakem numeric_override=null dışında değer veremez. Görev lease ve retry kayıtları kalıcıdır. Normal roller kritik tablolara doğrudan yazamaz; izinli RPC kullanır. Yerel SQLite dosyasına erişimi olan Python süreci güvenilir işçi kabul edilir; SQLite ağ kimlik doğrulama katmanı değildir.','', 'Rol katkısı ileride aynı walk-forward bölmelerinde ablation ile ölçülür. Şu anda yeni rollerin futbol tahmin başarısını artırdığına dair deney yapılmadı.']
    (root/'AGENT_ROLES.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'baseline_files_unchanged':len(records),'modules_inventoried':len(inventory),'roles':len(registry())}))
if __name__=='__main__':main()
