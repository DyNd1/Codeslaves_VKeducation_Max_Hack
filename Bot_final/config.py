import logging
from maxgram import Bot
from DATABASE.database import EducationDB

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Глобальные переменные
logger = logging.getLogger(__name__)
db = EducationDB()
bot = Bot("f9LHodD0cOIKHgVbM5Nzm2JyAu8KdVnGIv75mgcBK2TmH2VfYEG9gn9e4VClYCNCEpI3SRNGpFnI1Fu1w1en")