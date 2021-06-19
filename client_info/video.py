import json
from abr import Chunk
from client_info import BasicClient
class Clip:
    def __init__(self,file):
        with open(file) as f:
            data = json.load(f)
        self.period = data['period']
        self.repre_list = []
        for i in range(len(data['representation'])):
            now = data['representation'][0]
            self.repre_list.append(Chunk(now[0],now[1],now[2],now[3],now[4],
                                         now[5],now[6],now[7]
                                         ))
        #当前片段中在CDNs端所有可用的chunk

        '''
        repre_list = [
        [chunk_size,ssim,bitrate,resolution ratio]
        
        ]
        '''
        # both of them are List

if __name__ == "__main__":
    file_path = "/"
    client = BasicClient(1000,file_path,1)
    #abr = BBA(client)


