#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import re   #regexp
import sqlite3
import requests
import json
import logging
import os

logging.basicConfig(format = u'%(levelname)-8s [%(asctime)s] %(message)s',
                    level = logging.DEBUG, filename = u'/var/log/dlna_plugin.log',
                    filemode = 'w+')

def byDist(result):
    return result[1]

class CService(object):
    """Содержит настройки для сервиса"""
    def __init__(self, srv):
        self.api       = "https://api.themoviedb.org"
        self.searchPath = '/3/search/movie?api_key=' + srv["api_key"] + '&language=ru&query='

class Ctmdb(object):
 
    def __init__(self, config):
        self.__config = config
        self.__setService(1)
    
    def __setService(self, serviceId):
        for srv in self.__config['services']:
            if srv['id'] == serviceId:
                self.__service = CService(srv)
                break

    def __errGetData(self, movieInfo, fileName):
        if movieInfo['status_code'] == 34:
            logging.info( fileName+': '+movieInfo['status_message'] )
            #msg(fileName + ':', info)
            #msg(movieInfo['status_message'], info)
        else:
            logging.critical( movieInfo['status_message'] )
            #msg(movieInfo['status_message'], error)
            os._exit(13)

    def __correctName(self, fileName):
        cName = fileName
        cName = cName.replace(".", " ")
        cName = cName.replace("_", " ")
        return cName

    def findFilm(self, fileName):

        movieName = self.__correctName(fileName)
        response = requests.get(self.__service.api + self.__service.searchPath + movieName)

        if 200 == response.status_code:
            self.parseInfo = (response.json(), movieName)
            return True if self.parseInfo[0]['results'] else False

        elif response.status_code == 401 or response.status_code == 403:
            self.__errGetData(response.json(), fileName)
            return False
        else:
            logging.critical('Error connection, status:', response.status_code, ', Reason: ', response.reason, error)
            os._exit(13)

    def getImage(self, fileName):
        result = self.selectOneResult(fileName)
        if result:
            rawImage = requests.get('https://image.tmdb.org/t/p/w500/'+result['poster_path'])
            logging.info('Получено изображение для ' + fileName)
            return rawImage.content
        else:
            logging.warning(fileName + ' не найден в базе данных')
            return None

    def distance(self, a, b):
        "Calculates the Levenshtein distance between a and b."
        n, m = len(a), len(b)
        if n > m:
            # Make sure n <= m, to use O(min(n, m)) space
            a, b = b, a
            n, m = m, n

        current_row = range(n + 1)  # Keep current and previous row, not entire matrix
        for i in range(1, m + 1):
            previous_row, current_row = current_row, [i] + [0] * n
            for j in range(1, n + 1):
                add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
                if a[j - 1] != b[i - 1]:
                    change += 1
                current_row[j] = min(add, delete, change)

        return current_row[n]

    def selectOneResult(self, fileName):
        movieName = self.__correctName(fileName)
        movieInfo = self.parseInfo[0]['results']
        distanses = []
        if movieInfo:
            for inf in movieInfo:
                distanses.append((movieInfo.index(inf), self.distance(movieName, inf['original_title'])))
            distanses.sort(key=byDist)
            return movieInfo[distanses[0][0]]
        else:
            return None

class CDBworker(object):
    
    def getDBPath(self, pathToConfig):
        dlnaConfFile = open(pathToConfig, "r")
        f = dlnaConfFile.read()
        dbPath = re.search(r'[\n](db_dir=)(\/[\/\w]+)', f)
        dlnaConfFile.close()
        return dbPath.group(2)

    def getMovies(self):
        sql = 'SELECT TITLE FROM DETAILS WHERE DURATION AND ALBUM_ART=0;'
        self.cursor.execute(sql)
        self.movies = self.cursor.fetchall()

    def checkInfoTable(self):
        self.cursor.execute("""CREATE TABLE if NOT EXISTS INFO 
        ('id' INTEGER PRIMARY KEY AUTOINCREMENT, 'imdbID' INTEGER, 'fileName' TEXT);""")
        self.__conn.commit()

    def movieExist(self, name):
        sql = 'SELECT imdbID FROM INFO WHERE fileName=:file'
        self.cursor.execute(sql, {'file': name})
        result = self.cursor.fetchone()
        return True if result and result[0] != 0 else False

    def updateTables(self,fileName):
        #обновить DETAILS, INFO, ALBUM_ART
        sql = "INSERT INTO ALBUM_ART VALUES (Null, :path)"
        self.cursor.execute(sql, {'path': self.imageName(fileName)})
        self.__conn.commit()
        sql = 'SELECT ID FROM ALBUM_ART WHERE PATH=:path'
        self.cursor.execute(sql, {'path': self.imageName(fileName)})
        r = self.cursor.fetchone()
        imageId = r[0]
        movieInfo = self.tmbd.selectOneResult(fileName)
        if movieInfo:
            imdbID = movieInfo['id']
            sql = "INSERT INTO INFO VALUES (Null, :imdbID, :fileName)"
            self.cursor.execute(sql, {'imdbID': imdbID, 'fileName': fileName})
            self.__conn.commit()
            sql = """UPDATE DETAILS
                     SET TITLE = :nTitle
                     , ALBUM_ART = :id
                     WHERE TITLE =:oTitle AND DURATION AND ALBUM_ART=0
                    """
            self.cursor.execute(sql, 
                        {'nTitle': movieInfo['title'],
                         'id': imageId,
                         'oTitle': fileName})
            self.__conn.commit()


    def imageName(self, movieName):
        return self.art_cache + '/' + movieName + '.jpg'

    def exec(self):
        self.getMovies()
        self.checkInfoTable()
        for movie in self.movies:
            if not self.movieExist(movie[0]):
                if self.tmbd.findFilm(movie[0]):
                    image = self.tmbd.getImage(movie[0])
                    if image:
                        out = open(self.imageName(movie[0]), "wb")
                        out.write(image)
                        out.close()
                        self.updateTables(movie[0])
                    # print('Фильм ' + movie[0] + ' найден и добавлен')


    def __init__(self, config):
        logging.info( u'Начало сканирования' )
        self.config = config
        self.tmbd   = Ctmdb(config)
        path = self.getDBPath(config['minidlna'])
        self.art_cache =  path + '/art_cache'
        dbPath = path + '/files.db'
        try:
            self.__conn = sqlite3.connect(dbPath)
        except sqlite3.Error as e:
            logging.critical( e.args[0] )
            os._exit(2)

        self.cursor = self.__conn.cursor()
        self.exec()
        logging.info('Обработка завершена')