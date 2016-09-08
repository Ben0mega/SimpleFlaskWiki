import markdown
import git
import glob
import string
import html
import os.path
import errno
import os
from flask import Flask,render_template,Markup, request, redirect, url_for, send_file

app = Flask(__name__)

@app.route("/")
def index():
	try:
		return wiki_page('Main')
	except FileNotFoundError:
		return render_template('wiki_page.html', title='Main', content='Edit me')

@app.route('/pages/<name>')
def wiki_page(name):
	title = nameToTitle(name)
	file_ = nameToFileName(name)
	return render(title, file_)

def render(title, file_name):
	fn = getRender(getExtension(file_name))
	return fn(title, file_name)

def markDownRender(title, file_name):
	with open(file_name) as f:
		content = f.read()
	content = Markup(markdown.markdown(content))
	return render_template('wiki_page.html', content=content, title=title)

def binaryRender(title, file_name):
	return send_file(file_name)

def nameToTitle(name):
	name = sanitize(name)
	return name.replace('-', ' ')

# get file_name for name.  if content_type is specified, verify that the extension is correct
def nameToFileName(name, content_type=None):
	name = sanitize(name)
	if name == '':
		raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), name)
	files = glob.glob(os.path.join('pages', name+'.*'))
	assert(len(files) < 2)
	if len(files) == 0:
		if content_type == None:
			raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), name)
		# create name based on content type
		print(content_type)
		fname = os.path.join('pages', name+'.'+contentToExtension(content_type))
		files=[fname]
	if content_type != None:
		assert(getExtension(files[0]) == contentToExtension(content_type))
	return files[0]

def contentToExtension(content_type):
	if content_type == 'image/gif':
		extension = 'gif'
	elif content_type == 'image/png':
		extension = 'png'
	elif content_type == 'image/jpeg':
		extension = 'jpeg'
	elif content_type == 'text/plain':
		extension='md'
	else:
		extension = None

	assert(getRender(extension) != None)
	return extension

def isBinary(fn):
	ext = getExtension(fn)
	return getRender(ext) == binaryRender

def getExtension(fn):
	return fn.split('.')[-1]

def getRender(name_type):
	names_to_renderers = {
			'md' : markDownRender,
			'gif' : binaryRender,
			'jpeg' : binaryRender,
			'png' : binaryRender,
		}
	fn = names_to_renderers.get(name_type, None)
	return fn

def sanitize(name):
	def safe(a):
		if a in string.ascii_letters or a in string.digits or a =='_' or a=='-':
			return a
		return ''
	return ''.join(safe(a) for a in name)


@app.route('/edit/')
@app.route('/edit/<name>')
@app.route('/edit/<name>/<revision>')
def edit_page(name='', revision=None):
	title = nameToTitle(name)
	try:
		file_name = nameToFileName(name)
	except FileNotFoundError:
		file_name = "DISALLOWED\tNAME.jpeg"

	if isBinary(file_name):
		content = "BINARY/UNKNOWN/EMPTY FILE"
	else:
		content = html.escape(get_revision_content(file_name, revision))
	revisions = list((html.escape(c.message), c.hexsha) for c in get_revisions(file_name))
	print(revisions)
	return render_template('edit_page.html', content=content, title=title, revisions=revisions)

def get_revisions(file_name):
	repo = get_repo()
	file_name = dropTopLevelDir(file_name)
	return list(repo.iter_commits(paths=file_name))

def get_revision_content(file_name, revision_id):
	if revision_id is None:
		with open(file_name) as f:
			return f.read()

	repo = get_repo()
	commit = repo.commit(revision_id)
	file_name = dropTopLevelDir(file_name)
	data = (commit.tree/file_name).data_stream.read()
	print(data.decode('utf-8'))
	return data.decode('utf-8')

@app.route('/save/', methods=['POST'])
def save_page():
	name = request.form['title']
	content = request.form.get('content', None)
	msg = "User {0!s} @ IP {1!s} edited {2!s} with message: {3!s}".format(
			request.form['user'],
			request.remote_addr,
			name,
			request.form['msg']
			)

	try:
		fn = nameToFileName(name)
	except FileNotFoundError:
		# assume it is a markdown file for now...
		fn = nameToFileName(name, 'text/plain')

	file_ = request.files.get('file')
	if not file_:
		save_content(fn, content, msg)
		return redirect(url_for('wiki_page', name=name))

	# use the actual mimetype since we now have a file...
	fn = nameToFileName(name, file_.mimetype)
	save_content(fn, file_, msg)
	return redirect(url_for('wiki_page', name=name))

def save_content(fn, content, msg):
	#verify "pages" dir exists...
	repo = get_repo()

	if hasattr(content, 'save'):
		content.save(fn)
	else:
		with open(fn, 'w') as f:
			f.write(content)

	print(dropTopLevelDir(fn))
	print(msg)
	repo.index.add([dropTopLevelDir(fn)])
	repo.index.commit(msg)

def dropTopLevelDir(fn):
	path = os.path.split(fn)
	return os.path.join(*path[1:])

def get_repo():
	if not os.path.exists("pages"):
		repo = git.Repo.init('pages/')
		repo.index.commit('Init commit')
		return repo
	return git.Repo('pages/')

if __name__ == "__main__":
	app.run()
