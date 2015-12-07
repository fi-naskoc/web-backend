import falcon
from sqlalchemy import func, and_

from db import session
import model
import util
import datetime
import json
import re

class Correction(object):
	"""
	GET pozadavek na konkretni correction se spousti prevazne jako odpoved na POST
	id je umele id, konstrukce viz util/correction.py
	Parametry: moduleX_version=Y (X a Y jsou cisla)
	"""
	def on_get(self, req, resp, id):
		user = req.context['user']
		year = req.context['year']
		task = int(id) / 100000
		participant = int(id) % 100000

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		# Ziskame prislusna 'evaluation's
		corrs = session.query(model.Evaluation, model.Task, model.Module).\
			filter(model.Evaluation.user == participant).\
			join(model.Module, model.Module.id == model.Evaluation.module).\
			join(model.Task, model.Task.id == model.Module.task).\
			join(model.Wave, model.Task.wave == model.Wave.id).\
			join(model.Year, model.Year.id == model.Wave.year).\
			filter(model.Year.id == year).\
			filter(model.Task.id == task)

		task_id = corrs.group_by(model.Task).first()
		if task_id is None:
			resp.status = falcon.HTTP_404
			return

		task_id = task_id.Task.id
		corr_evals = corrs.group_by(model.Evaluation).all()
		corr_modules = corrs.group_by(model.Module).all()

		# Parsovani GET pozadavku:
		specific_evals = {}
		for param in req.params:
			module = re.findall(r'\d+', param)
			if module: specific_evals[int(module[0])] = session.query(model.Evaluation).get(req.get_param_as_int(param))

		req.context['result'] = {
			'correction': util.correction.to_json([ (corr, mod, specific_evals[mod.id] if mod.id in specific_evals else None) for (corr, task, mod) in corr_modules ], [ evl for (evl, tsk, mod) in corr_evals ], task_id)
		}

	# PUT: propojeni diskuzniho vlakna komentare
	def _process_thread(self, corr):
		curr_thread = util.task.comment_thread(corr['task_id'], corr['user'])

		if (corr['comment'] is not None) and (curr_thread is None):
			# pridavame diskuzni vlakno
			try:
				comment = model.SolutionComment(thread=corr['comment'], user=corr['user'], task=corr['task_id'])
				session.add(comment)
				session.commit()
			except:
				session.rollback()
				raise
			finally:
				session.close()

		if (corr['comment'] is None) and (curr_thread is not None):
			# mazeme diskuzni vlakno
			try:
				comment = session.query(model.SolutionComment).get((curr_thread, corr['user'], corr['task_id']))
				session.delete(comment)
				session.commit()
			except:
				session.rollback()
				raise

	# PUT: pridavani a mazani achievementu
	def _process_achievements(self, corr):
		a_old = util.achievement.ids_list(util.achievement.per_task(corr['user'], corr['task_id']))
		a_new = corr['achievements']
		if a_old != a_new:
			# achievementy se nerovnaji -> proste smazeme vsechny dosavadni a pridame do db ty, ktere nam prisly
			for a_id in a_old:
				try:
					session.delete(session.query(model.UserAchievement).get((corr['user'], a_id, corr['task_id'])))
					session.commit()
				except:
					session.rollback()
					raise

			for a_id in a_new:
				try:
					ua = model.UserAchievement(user_id=corr['user'], achievement_id=a_id, task_id=corr['task_id'])
					session.add(ua)
					session.commit()
				except:
					session.rollback()
					raise
				finally:
					session.close()

	# PUT: zpracovani hodnoceni
	def _process_evaluation(self, data_eval, user_id):
		try:
			evaluation = session.query(model.Evaluation).get(data_eval['eval_id'])
			if evaluation is None: return
			evaluation.points = data_eval['points']
			evaluation.time = datetime.datetime.utcnow()
			print data_eval['corrected_by']
			evaluation.evaluator = data_eval['corrected_by'] if 'corrected_by' in data_eval else user_id
			evaluation.full_report += str(datetime.datetime.now()) + " : edited by org " + str(user_id) + " : " + str(data_eval['points']) + " points" + '\n'
			session.commit()
		except:
			session.rollback()
			raise

	# PUT: zpracovani hodnoceni modulu
	def _process_module(self, data_module, user_id):
		self._process_evaluation(data_module['evaluation'], user_id)

	# PUT ma stejne argumenty, jako GET
	def on_put(self, req, resp, id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		corr = json.loads(req.stream.read())['correction']

		self._process_thread(corr)
		self._process_achievements(corr)

		for module in corr['modules']:
			self._process_module(module, user.id)

		# odpovedi jsou updatnute udaje
		self.on_get(req, resp, id)

###############################################################################

class Corrections(object):

	"""
	Specifikace GET pozadavku:
	musi byt vyplnen alespon jeden z argumentu:
	?task=task_id
	?participant=user_id
	"""
	def on_get(self, req, resp):
		user = req.context['user']
		year = req.context['year']
		task = req.get_param_as_int('task')
		participant = req.get_param_as_int('participant')

		if task is None and participant is None:
			resp.status = falcon.HTTP_400
			return

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		# Ziskame prislusna 'evaluation's
		corrs = session.query(model.Evaluation, model.Task, model.Module, model.Thread.id.label('thread_id'))
		if participant is not None:
			corrs = corrs.filter(model.Evaluation.user == participant)
		corrs = corrs.join(model.Module, model.Module.id == model.Evaluation.module).\
			join(model.Task, model.Task.id == model.Module.task).\
			join(model.Wave, model.Task.wave == model.Wave.id).\
			join(model.Year, model.Year.id == model.Wave.year).\
			filter(model.Year.id == year)
		if task is not None:
			corrs = corrs.filter(model.Task.id == task)
		corrs = corrs.outerjoin(model.SolutionComment, and_(model.SolutionComment.user == model.Evaluation.user, model.SolutionComment.task == model.Task.id)).\
			outerjoin(model.Thread, model.SolutionComment.thread == model.Thread.id)

		# Evaluations si pogrupime podle uloh, podle toho vedeme result a pak pomocne podle modulu (to vyuzivame pri budovani vystupu)
		corrs_tasks = corrs.group_by(model.Task, model.Evaluation.user).all()
		corrs_modules = corrs.group_by(model.Module, model.Evaluation.user).all()
		corrs_evals = corrs.group_by(model.Evaluation, model.Evaluation.user).all()

		# Achievementy po ulohach a uzivatelich:
		corrs_achs = session.query(model.Task.id, model.UserAchievement.user_id.label('user_id'), model.Achievement.id.label('a_id'))
		if task is not None: corrs_achs = corrs_achs.filter(model.Task.id == task)
		if participant is not None: corrs_achs = corrs_achs.filter(model.UserAchievement.user_id == participant)
		corrs_achs = corrs_achs.join(model.UserAchievement, model.UserAchievement.task_id == model.Task.id).\
			join(model.Achievement, model.Achievement.id == model.UserAchievement.achievement_id).\
			group_by(model.Task, model.UserAchievement.user_id, model.Achievement).all()

		# ziskame vsechny plne opravene ulohy:
		tasks_corrected = util.correction.tasks_corrected()

		# Vsechny achievementy
		achievements = session.query(model.Achievement).\
			filter(model.Achievement.year == req.context['year']).all()

		# Argumenty (a jejich format) funkce util.correction.to_json popsany v ~/util/correction.py

		req.context['result'] = {
			'corrections': [ util.correction.to_json( \
					[ (evl, mod, None) for (evl, tsk, mod, thr) in filter(lambda x: x.Task.id == corr.Task.id and x.Evaluation.user == corr.Evaluation.user, corrs_modules) ],\
					[ evl for (evl, tsk, mod, thr) in filter(lambda x: x.Task.id == corr.Task.id and x.Evaluation.user == corr.Evaluation.user, corrs_evals) ],\
					filter(lambda x: x.Task.id == corr.Task.id and x.Evaluation.user == corr.Evaluation.user, corrs_evals)[0].Task.id,\
					corr.thread_id,\
					[ r for (a,b,r) in filter(lambda (task_id, user_id, a_id): task_id == corr.Task.id and user_id == corr.Evaluation.user, corrs_achs) ],\
					corr.Task.id in tasks_corrected ) \
				for corr in corrs_tasks ],
			'tasks': [ util.correction.task_to_json(q.Task) for q in corrs.group_by(model.Task).all() ],
			'modules': [ util.correction.module_to_json(q.Module) for q in corrs.group_by(model.Module).all() ],
			'achievements': [ util.achievement.to_json(achievement) for achievement in achievements ]
		}
