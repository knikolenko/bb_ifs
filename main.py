import lzo
import os
import struct
import sys

class BlackBerryIFSReader:
    def __init__(self, fileName = None, outDir = None):
        self.HEADER_OFFSET = 0x1000
        self.FILE_NAME = fileName
        self.OUT_DIR = outDir

    @staticmethod
    def readAsciizStr(file):
        str = ''
        while True:
            c = file.read(1)
            if c == '\x00':
                break
            str += c

        return str

    def __isDir(self, header, fatItem):
        offset = fatItem['dataOffset']
        fatBlockStart = header['fatBlock']['offset']
        fatBlockEnd = fatBlockStart + header['fatBlock']['size']
        if offset >= fatBlockStart and offset <= fatBlockEnd:
            return True
        else:
            if offset == 0:
                return True
            else:
                return False

    def __fatOffsetToIndex(self, header, offset):
        fatBlockStart = header['fatBlock']['offset']
        return int((offset-fatBlockStart)/32)

    def __readBlockInfo(self, file):
        offset, size, = struct.unpack('<II', file.read(8))
        return {'offset': offset, 'size': size}

    def __readFatItem(self, file):
        s = file.read(32)
        unk1, unk2, name_offset, data_offset, size, unk3, unk4, unk5, = struct.unpack('<8I', s)
        return {'nameOffset': name_offset,
                'dataOffset': data_offset,
                'size': size
                }

    def __parseFat(self, file, header, fat, idx, count, path):
        for i in range(idx, idx+count):
            item = fat[i]
            file.seek(item['nameOffset'])
            item['name'] = path + self.readAsciizStr(file)
            # print 'FAT %d Name: %s' % (i, item['name'])

            print self.OUT_DIR + item['name']
            if self.__isDir(header, item):
                idx = self.__fatOffsetToIndex(header, item['dataOffset'])
                count = int(item['size'] / 32)
                os.makedirs(self.OUT_DIR+item['name']+os.sep)
                self.__parseFat(file, header, fat, idx, count, item['name']+os.sep)
            else:
                #print 'offset: %x size: %x' % (item['dataOffset'], item['size'])
                file.seek(item['dataOffset'])
                #raw = file.read(item['size'])
                raw = ''
                try:
                    headerSize, = struct.unpack('<I', file.read(4))
                    if headerSize > item['size']:
                        #packed or symlink
                        file.seek(item['dataOffset'])
                        data = file.read(item['size'])
                        open(self.OUT_DIR + item['name'], 'wb').write(data)
                        continue
                    headerSize -= 4
                    partOffsets = []
                    for j in range(0, headerSize/4):
                        packSize, = struct.unpack('<I', file.read(4))
                        partOffsets.append(packSize)
                    #print partOffsets
                    prevSize = headerSize+4
                    unpFile = ''
                    for o in partOffsets:
                        raw = file.read(o-prevSize)
                        prevSize = o
                        #print raw[:16].encode('hex')
                        #print raw[-16:].encode('hex')
                        unpFile += lzo.decompress(raw, False, item['size'])
                    #print unpFile
                    open(self.OUT_DIR+item['name'], 'wb').write(unpFile)
                except Exception, e:
                    #print e.message
                    print 'Unable unpack ' + self.OUT_DIR+item['name']
                    #print raw

    def __readFat(self, file, header):
        file.seek(header['fatBlock']['offset'])
        FAT = []
        for i in range(0, int(header['fatBlock']['size']/32)):
            FAT.append(self.__readFatItem(file))
        self.__parseFat(file, header, FAT, 0, 1, '')

    def __readHeader(self, file):
        trash, sign, unk1, unk2, = struct.unpack('<32s8sII', file.read(48))
        null_block = self.__readBlockInfo(file)
        fat_block = self.__readBlockInfo(file)
        names_block = self.__readBlockInfo(file)
        data_block = self.__readBlockInfo(file)

        return {'sign': sign,
                'nullBlock': null_block,
                'fatBlock': fat_block,
                'namesBlock': names_block,
                'dataBlock': data_block
                }

    def process(self, fileName = None, outDir = None):
        if fileName:
            self.FILE_NAME = fileName
        if outDir:
            self.OUT_DIR = outDir

        if not self.FILE_NAME:
            raise Exception('Incorrect file name')

        if not self.OUT_DIR:
            self.OUT_DIR = os.path.splitext(self.FILE_NAME)[0]

        file = open(self.FILE_NAME, 'rb')
        file.seek(self.HEADER_OFFSET)
        header = self.__readHeader(file)
        #print header
        self.__readFat(file, header)
        file.close()

if len(sys.argv) != 2:
    print 'Usage:'
    print '  %s <file_name>'%sys.argv[0]
    exit()

bbifs = BlackBerryIFSReader(sys.argv[1])
print 'Processing...'
bbifs.process()
print 'Done!'
