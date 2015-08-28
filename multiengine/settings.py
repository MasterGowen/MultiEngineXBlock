from path import path
USE_I18N=True
USE_L10N = True
TIME_ZONE = 'Asia/Yekaterinburg'
LANGUAGE_CODE = 'ru-RU'

PROJECT_ROOT = path(__file__).abspath().dirname()
LOCALE_PATHS = (PROJECT_ROOT + '/conf/locale',)
GIT_REPO_URL = 'https://github.com/MasterGowen/multiengine-scenarios.git'