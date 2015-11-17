import json
import os

from db import session
import model
import subprocess

"""
Specifikace \data v databazi modulu pro "text":
	text = {
		inputs = 3
		diff = ["spravne_reseni_a", "spravne_reseni_b", "spravne_reseni_c"]
		eval_script = "/path/to/eval/script.py"
		ignore_case = True
	}
Kazdy modul muze mit jen jeden text (s vice inputy).
"""

def to_json(db_dict, user_id):
	return { 'inputs': db_dict['text']['inputs'] }

def eval_text(eval_script, data, report):
	cmd = ['/usr/bin/python', eval_script] + data
	f = open('/tmp/eval.txt', 'w')
	process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
	process.wait()
	f.close();
	f = open('/tmp/eval.txt', 'r')
	report += f.read()

	return (process.returncode == 0, report)

def evaluate(task, module, data):
	report = '=== Evaluating text id \'%s\' for task id \'%s\' ===\n\n' % (module.id, task)
	report += ' Raw data: ' + json.dumps(data) + '\n'
	report += ' Evaluation:\n'

	text = json.loads(module.data)['text']

	if 'diff' in text:
		orig = text['diff']
		result = True
		report += 'Diff used!\n'
		for o, item in zip(orig, data):
			s1 = o.rstrip().lstrip().encode('utf-8')
			s2 = item.rstrip().lstrip().encode('utf-8')
			if ('ignore_case' in text) and (text['ignore_case']):
				s1 = s1.lower()
				s2 = s2.lower()
			print("Compare: " + s1 + ", " + s2 +", " + str(s1 == s2))
			result = result and s1 == s2
		if len(data) != len(orig):
			result = False
		return (result, report)
	elif 'eval_script' in text:
		return eval_text(text['eval_script'], data, report)
	else:
		report += 'No eval method specified!\n'
		return (False, report)
