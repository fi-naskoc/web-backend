import smtplib
from email.mime.text import MIMEText

KSI = 'ksi@fi.muni.cz'
FEEDBACK = [ 'email@honzamrazek.cz', 'henrich.lau@gmail.com' ]

def send(to, subject, text, addr_from=KSI):
	msg = MIMEText(text.encode('utf-8'))

	msg['Subject'] = subject
	msg['From'] = addr_from
	msg['To'] = ','.join(to)

	s = smtplib.SMTP('relay.muni.cz')
	s.sendmail(addr_from, to if isinstance(to, (list)) else [ to ], msg.as_string())
	s.quit()

def send_feedback(text, addr_from):
	addr_from = addr_from if len(addr_from) > 0 else KSI

	send(FEEDBACK, '[KSI-WEB] Zpetna vazba', text, addr_from)