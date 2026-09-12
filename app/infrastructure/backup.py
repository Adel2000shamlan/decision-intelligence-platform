from pathlib import Path
import hashlib, shutil
class BackupManager:
    def backup(self,source,destination):
        src=Path(source); dst=Path(destination)
        if not src.exists(): raise FileNotFoundError(src)
        dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        if self.sha256(src)!=self.sha256(dst): raise IOError('backup checksum verification failed')
        return dst
    def restore(self,backup,destination): return self.backup(backup,destination)
    def sha256(self,path):
        h=hashlib.sha256()
        with Path(path).open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
        return h.hexdigest()
