import os
import subprocess
import csv
import pprint
import sys
import glob
# import is_bin
import json
import argparse

def is_bin(fname):
	targets = [ ".o", ".a", ".so" ]
	base_name, ext = os.path.splitext(fname)
	if ext in targets:
		return True
	else:
		return False

def exec_subprocess(cmd: str, raise_error=True):
	child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = child.communicate()
	rt = child.returncode
	if rt != 0 and raise_error:
		raise Exception(f"Command return code is not 0, got {rt}, stderr = {stderr}")
	return stdout, stderr, rt

def convert_fields(fields):
	ret_fields = []
	state_regex = False
	tmp_field = ""
	for field in fields:
		# print(field)
		if state_regex is False:
			if field.startswith('/^'):
				if field.endswith('/;"'):
					ret_fields.append(field)
				else:
					tmp_field = field
					state_regex = True
			else:
				ret_fields.append(field)
		else:
			# state_regex = True
			if field.endswith('/;"'):
				tmp_field = tmp_field + "\t" + field
				ret_fields.append(tmp_field)
				state_regex = False
			else:
				tmp_field += "\t" + field
	return ret_fields

def make_tags(debug=False):
	flist = glob.glob('./**', recursive=True)
	tags = {}
	ftags = {}
	for fname in flist:
		if debug:
			print(fname)
		if os.path.isfile(fname) and not is_bin(fname):
		# if os.path.isfile(fname):
			stdout, stderr, rt = exec_subprocess("ctags -f- --fields=+afmikKlnsStz {}".format(fname))
			lines = stdout.decode('utf-8', errors='ignore').split('\n')
			for line in lines:
				# fields = line.split('[\t]+')
				fields_tmp = line.split('\t')
				fields = list(filter(lambda a: a != '', fields_tmp))
				if debug:
					print(fields)
				# [0]: tag, [1]: fname, [2]: regex, [3]: type, [4]: row-num, [5]: file scope
				if len(fields) > 4:
					fields = convert_fields(fields)
					if debug:
						print(fields)
					if not fields[1] in ftags:
						ftags[fields[1]] = []

					tags["name"] = fields[0]
					tags["lstart"] = int(fields[4].split(':')[1])
					tags["kind"] = fields[3].split(':')[1]
					tags["lang"] = fields[5].split(':')[1]
					ftags[fields[1]].append(tags)
					tags = {}
	if debug:
		pprint.pprint(ftags)
	with open('./tags.json', 'w') as f:
		json.dump(ftags, f, indent=2)

	return ftags

def load_tags(debug=False):
	with open('./tags.json', 'r') as f:
		ftags = json.load(f)
	return ftags

def print_and_fout(output: str):
	print(output)
	with open("./calltree.md", "a") as f:
		f.write(output + "\n")

def show_func_info(fncname, exlibs):
	if fncname == "":
		# little bit weired but nothing to do.
		return 
	exfunc_str = ""
	explain = ""
	if fncname.startswith("trace_"):
		explain = ": trace_ is automatic generated function"
		
	for k in exlibs:
		for e in exlibs[k]:
			if e["name"] == fncname:
				exfunc_str = e["url"]
				break
		else:
			continue
		break
	print_and_fout("  - [{}]({}) {}".format(fncname, exfunc_str, explain))
	

def cflows(fname: str, fn: str, ty: str, st: int, en: int, exlibs, debug=False):
	tmp = "./tmptmptmp"
	if ty == "C" or ty == "C++":
		pass
	else:
		return

	stdout, stderr, rt = exec_subprocess("sed -n '{},{}p' {}".format(st, en, fname))
	with open(tmp, "w") as f:
		f.write(stdout.decode(errors='ignore'))
	stdout, stderr, rt = exec_subprocess("cflow {}".format(tmp))
	lines = stdout.decode(errors='ignore').split('\n')
	lines = lines[1:]
	print_and_fout("- [{}]({})".format(fn, fname))
	for line in lines:
		ln = line.lstrip()
		if debug:
			print(ln)
		ln_nm = ln.replace('(','').replace(')','')
		show_func_info(ln_nm, exlibs)
	os.remove(tmp)

def is_function(d):
	return True if d["kind"] == 'function' else False

def show_funcs(fname, func_filtered, exlibs, debug=False):
	maxline = len(open(fname).readlines())
	n = len(func_filtered)
	for i, d in enumerate(func_filtered):
		st = func_filtered[i]["lstart"]
		if i == n-1:
			en = maxline
		else:
			en = func_filtered[i+1]["lstart"]
		cflows(fname, func_filtered[i]["name"], func_filtered[i]["lang"], st, en, exlibs, debug)

def show_flow(ftags, debug=False):
	with open("./exlibs.json", "r") as f:
		exlibs = json.load(f)
	for fname in ftags:
		if debug:
			print(fname)
		# pprint.pprint(ftags[fname])
		lnum_sorted = sorted(ftags[fname], key=lambda x:x['lstart'])
		func_filtered = list(filter(is_function, lnum_sorted))
		if debug:
			pprint.pprint(func_filtered)
		show_funcs(fname, func_filtered, exlibs, debug)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="partitional job")
	parser.add_argument('-t', '--tags', action='store_true')
	parser.add_argument('-f', '--flow', action='store_true')
	parser.add_argument('-d', '--debug', action='store_true')
	args = parser.parse_args()
	if args.tags:
		ftags = make_tags(args.debug)
	else:
		ftags = load_tags(args.debug)

	if args.flow:
		show_flow(ftags, args.debug)
	else:
		pass
