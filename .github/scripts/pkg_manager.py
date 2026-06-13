import os
import sys
import json
import re
import tarfile

def parse_makefile(filepath):
    pkgs, vars_dict = set(), {}
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for line in content.splitlines():
                m_var = re.match(r'^([A-Za-z0-9_]+)\s*:?=\s*(.+)', line)
                if m_var: vars_dict[m_var.group(1).strip()] = m_var.group(2).strip()

            def expand_vars(text):
                for _ in range(5):
                    matches = re.findall(r'\$\(([A-Za-z0-9_]+)\)', text)
                    if not matches: break
                    for m in matches: text = text.replace(f"$({m})", vars_dict.get(m, ""))
                return text

            for m_pkg in re.finditer(r'^define Package/([^\s/]+)\s*$', content, re.M):
                expanded = expand_vars(m_pkg.group(1).strip())
                if expanded: pkgs.add(expanded.lower())

            if 'luci.mk' in content:
                if 'LUCI_NAME' in vars_dict: pkgs.add(expand_vars(vars_dict['LUCI_NAME']).lower())
                elif 'PKG_NAME' in vars_dict: pkgs.add(expand_vars(vars_dict['PKG_NAME']).lower())
                else: pkgs.add(os.path.basename(os.path.dirname(filepath)).lower())
            
            if not pkgs and 'PKG_NAME' in vars_dict: pkgs.add(expand_vars(vars_dict['PKG_NAME']).lower())
    except: pass
    return {p for p in pkgs if p}

def extract_real_pkgname(filepath):
    try:
        with tarfile.open(filepath, 'r:*') as tar:
            try:
                pkginfo = tar.extractfile('.PKGINFO')
                if pkginfo:
                    for line in pkginfo.read().decode('utf-8').splitlines():
                        if line.startswith('pkgname = '): return line.split('=')[1].strip()
            except KeyError: pass
            for member in tar.getmembers():
                if member.name.endswith('control.tar.gz'):
                    ctar_f = tar.extractfile(member)
                    with tarfile.open(fileobj=ctar_f, mode='r:gz') as ctar:
                        for cmember in ctar.getmembers():
                            if cmember.name.endswith('control'):
                                cfile = ctar.extractfile(cmember)
                                for line in cfile.read().decode('utf-8').splitlines():
                                    if line.startswith('Package: '): return line.split(':')[1].strip()
    except: pass
    
    base = os.path.basename(filepath)
    if base.endswith('.apk'):
        m = re.match(r'^(.+?)-[0-9]', base)
        if m: return m.group(1)
    elif base.endswith('.ipk'):
        m = re.match(r'^([^_]+)', base)
        if m: return m.group(1)
    return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 pkg_manager.py <mode> ...")

    mode = sys.argv[1]

    # ==========================================
    # 模式 1：检查 Makefile (全量 full 或 增量 check/inc)
    # ==========================================
    if mode in ['full', 'inc', 'check']:
        if len(sys.argv) < 7:
            sys.exit(f"Usage: python3 pkg_manager.py {mode} <repo_dir> <state_file> <out_config> <out_list> <new_state_file>")
            
        repo_dir = sys.argv[2]
        state_file = sys.argv[3]
        out_config = sys.argv[4]
        out_list = sys.argv[5]
        new_state_file = sys.argv[6]

        old_state = {}
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f: old_state = json.load(f)
            except: pass

        new_state, configs, compile_list, changed_pkgs = {}, [], [], set()

        # 🌟 核心逻辑变更：遍历一级目录
        for item in os.listdir(repo_dir):
            top_dir = os.path.join(repo_dir, item)
            
            # 过滤掉文件和隐藏目录（如 .git, .github）
            if not os.path.isdir(top_dir) or item.startswith('.'):
                continue
                
            commit_hash = "NEW"
            commit_file = os.path.join(top_dir, '.upstream_commit')
            if os.path.exists(commit_file):
                try:
                    with open(commit_file, 'r') as f: commit_hash = f.read().strip()
                except: pass
            
            # 缓存字典现在的 Key 是一级目录名（如 'OpenClash'）
            new_state[item] = commit_hash
            
            need_build = False
            if mode == 'full':
                need_build = True
            elif mode in ['inc', 'check']:
                if old_state.get(item) != commit_hash:
                    need_build = True
                    print(f"🔄 Changes detected in top-level directory: {item} (Hash: {commit_hash})")
            
            # 只有当该一级目录判定需要编译时，才去向下搜寻所有的 Makefile
            if need_build:
                for root, dirs, files in os.walk(top_dir):
                    if 'Makefile' in files:
                        rel_path = os.path.relpath(root, repo_dir)
                        pkgs = parse_makefile(os.path.join(root, 'Makefile'))
                        if pkgs:
                            compile_list.append(f"{root}:{' '.join(pkgs)}")
                            for p in pkgs:
                                configs.append(f"CONFIG_PACKAGE_{p}=m")
                                changed_pkgs.add(p)
                                print(f"✅ Queued: {p} (from {rel_path})")
                                
                                if p == "lanspeedd":
                                    configs.append("CONFIG_PACKAGE_lanspeedd-bpf=m")
                                    changed_pkgs.add("lanspeedd-bpf")
                                    print(f"✅ Auto-queued BPF extension: lanspeedd-bpf (from {rel_path})")
                                
                                # 自动追加 smartdns-ui
                                # if p == "smartdns":
                                #     configs.append("CONFIG_PACKAGE_smartdns-ui=m")
                                #     changed_pkgs.add("smartdns-ui")
                                #     print(f"✅ Auto-queued UI extension: smartdns-ui (from {rel_path})")

        with open('/tmp/changed_pkgs.txt', 'w') as f: f.write('\n'.join(changed_pkgs))
        with open(out_config, 'a') as f: f.write('\n'.join(configs) + '\n')
        with open(out_list, 'w') as f: f.write('\n'.join(compile_list) + '\n')
        os.makedirs(os.path.dirname(new_state_file), exist_ok=True)
        with open(new_state_file, 'w') as f: json.dump(new_state, f, indent=2)

    elif mode == 'plan_sync':
        if len(sys.argv) < 4:
            sys.exit("Usage: python3 pkg_manager.py plan_sync <new_pkgs_list> <dest_dir>")
            
        new_pkgs_list = sys.argv[2]
        dest_dir = sys.argv[3]
        
        if not os.path.exists(new_pkgs_list): sys.exit(0)
        
        explicit_pkgs = set()
        if os.path.exists('/tmp/changed_pkgs.txt'):
            with open('/tmp/changed_pkgs.txt', 'r') as f: explicit_pkgs = set(f.read().splitlines())
            
        with open(new_pkgs_list, 'r') as f: new_files = f.read().splitlines()
        
        to_copy, to_delete = [], []
        for file in new_files:
            if not os.path.exists(file): continue
            pkgname = extract_real_pkgname(file)
            basename = os.path.basename(file)
            if not pkgname: continue
          
            if pkgname not in explicit_pkgs and os.path.exists(os.path.join(dest_dir, basename)):
                print(f"🛡️ Ignored dependency false-update: {basename}")
                continue
                
            to_copy.append(file)
            
            if os.path.exists(dest_dir):
                for ext_f in os.listdir(dest_dir):
                    if ext_f.endswith('.apk') or ext_f.endswith('.ipk'):
                        if ext_f.startswith(f"{pkgname}-") or ext_f.startswith(f"{pkgname}_"):
                            if extract_real_pkgname(os.path.join(dest_dir, ext_f)) == pkgname:
                                to_delete.append(os.path.join(dest_dir, ext_f))
                                
        with open('/tmp/copy_list.txt', 'w') as f: f.write('\n'.join(to_copy))
        with open('/tmp/delete_list.txt', 'w') as f: f.write('\n'.join(to_delete))
