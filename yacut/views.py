from flask import abort, flash, redirect, render_template
from sqlalchemy.exc import SQLAlchemyError

from . import app, db
from .disk import DiskError, upload_files
from .forms import FilesForm, URLForm
from .models import URLMap, get_unique_short_id  # noqa: F401


@app.route('/', methods=['GET', 'POST'])
def index_view():
    form = URLForm()
    short_link = None
    if form.validate_on_submit():
        try:
            item = URLMap.create(form.original_link.data, form.custom_id.data)
            short_link = item.short_link
        except ValueError as error:
            flash(str(error), 'danger')
    return render_template('index.html', form=form, short_link=short_link)


@app.route('/files', methods=['GET', 'POST'])
async def files_view():
    form = FilesForm()
    links = []
    if form.validate_on_submit():
        try:
            results = await upload_files(form.files.data)
        except DiskError as error:
            flash(str(error), 'danger')
        else:
            for file, result in zip(form.files.data, results):
                if isinstance(result, DiskError):
                    flash(str(result), 'danger')
                    continue
                if isinstance(result, Exception):
                    app.logger.warning('Disk upload failed: %s',
                                       type(result).__name__)
                    flash(f'Не удалось загрузить {file.filename}. '
                          'Проверьте доступ к Диску и повторите попытку.',
                          'danger')
                    continue
                filename, download_url = result
                try:
                    item = URLMap.create(download_url)
                except (ValueError, RuntimeError, SQLAlchemyError) as error:
                    db.session.rollback()
                    app.logger.warning('Short link creation failed: %s',
                                       type(error).__name__)
                    flash(f'Не удалось создать короткую ссылку для '
                          f'{filename}. Повторите попытку.', 'danger')
                    continue
                links.append((filename, item.short_link))
    return render_template('files.html', form=form, links=links)


@app.route('/<string:short_id>')
def redirect_view(short_id):
    item = URLMap.get(short_id)
    if item is None:
        abort(404)
    return redirect(item.original)
