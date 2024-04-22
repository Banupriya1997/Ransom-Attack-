#import statements required to execute the code below
import struct
import os
#creating FAT class with function to recover the files from a disk which is partially wipped
class FAT:
    #init function to read the disk image file and initialize the boot values
    def __init__(self,fatimagefile):
        #opening the image file in read mode
        self.fat= open(fatimagefile, 'rb' )
        #calling the function which calculated all the boot sector values
        self.getBootSectorValues()
    #function to set the cureent file position in the file stream of a disk image
    def getSector(self,sector:int)->bytes:
        #set the current file position at the required sector in the disk image file using seek() method
        self.fat.seek( sector * self.BytsPerSec )
        #reading the 512 bytes of the sector set by the seek () method
        return self.fat.read(self.BytsPerSec)

    #function to read the data bytes from given sector of the disk image
    def getBootSectorValues(self):
        #assigning the BytsPerSec to 512 for use till the original value is calculated from boot sector
        self.BytsPerSec = 512
        #Boot Sector or Reserved region is always present at the begining of the disk image which is sector 0
        #setting the current file position to the sector of interest 
        boot_block=self.getSector(0)
        #Unpack the values of obtained from the boot sector until 40 bytes using offset value '<3s8sHBHBHHBHHHLLL'
        self.jmpBoot, self.OemName, self.BytsPerSec, self.SecPerClus, \
        self.ResvdSecCnt, self.NumFATs, self.RootEntCnt, \
        self.TotSec16, self.Media, self.FATSz16, self.SecPerTrk, \
        self.NumHeads, self.HiddSec, self.TotSec32, self.FATSz32 = \
        struct.unpack( '<3s8sHBHBHHBHHHLLL', boot_block[ : 40 ] )
        #printing the values calculated in boot sector
        print("\n")
        print("----------------------------Reserved region details of the disk image--------------------------------")
        print(f"Bytes Per Sector: {self.BytsPerSec}\nSectors Per Cluster: {self.SecPerClus}\nReserved Sector Count : {self.ResvdSecCnt}\nNumber of FAT: {self.NumFATs}\nRoot Directory Entry: {self.RootEntCnt}\nTotal Number of Sector (16-bit): {self.TotSec16}\n ")
        self.getRootSectorValues()
    #function to get directories and files related information
    def getRootSectorValues(self):
        #RootDirSectors is the count of sectors occupied by root directory
        self.RootDirSectors = int(((self.RootEntCnt * 32 )+ self.BytsPerSec - 1 ) /self.BytsPerSec )
        #calculating the starting sector of the root directory
        self.RootDirStart = self.ResvdSecCnt + (self.NumFATs * self.FATSz16)
        #printing the values calculated in root directory
        print("-----------------------------Root Directory details of disk image-----------------------------------")
        print(f'Root Directory Start:{self.RootDirStart}\nTotal Root Directory Sectors:{self.RootDirSectors}')
        data=False
        #looping through the root directory sectors to check if its empty 
        for val in range(self.RootDirSectors):
            root_data=self.getSector(self.RootDirStart+val).decode('utf-8')
            if(root_data !=''):
                data=True
        if(not(data)):
            print("Root directory is empty !!!")
        #calling the function to get the list of file and directory names
        self.getdirectoryandfiles()
    #function to get the list of file and directory names
    def getdirectoryandfiles(self):
        #FirstDataSector is start of data region
        self.FirstDataSector = self.ResvdSecCnt + (self.NumFATs * self.FATSz16 ) + self.RootDirSectors
        #count of sectors in data region of the volume
        self.DataSec = self.TotSec16 - ( self.ResvdSecCnt +( self.NumFATs * self.FATSz16 ) + self.RootDirSectors )
        #count of cluster
        self.CountOfClusters = int( self.DataSec / self.SecPerClus )
        #start of Fat 
        self.FATStart = self.ResvdSecCnt 
        #printing the fat region details
        print("\n")
        print("--------------------------FAT region details of disk image-------------------------------")
        print(f'First Data Sector: {self.FirstDataSector}\nTotal FAT Data Sectors: {self.DataSec}\nCountOfClusters: {self.CountOfClusters}\nFAT Start Sector: {self.FATStart}')
        #initializing dictionaries to store the directories and files details
        self.dir_folder={}
        self.dir_folder_list={}
        self.start_cluster={}
        self.file_size={}
        #initializing variables 
        dir=1
        file=1
        set=1
        #looping through the sectors in the FAT starting from the first data sector till the total number of sectors
        for sec in range(self.FirstDataSector,self.TotSec16):
            #fetching the 512 bytes of the sector by using seek() and read
            sector_data_512=self.getSector(sec)
            #checking if the 512 bytes are not empty before traversing through them 
            if(sector_data_512 != b'\x00'*512):
                #initializing the start and end values to slice the 512 bytes to a set of 32 bytes to make it easier to read the directory_attributes( which is 32 bytes) 
                # such as dir_name, file_size, starting cluster etc
                start=0
                end=32
                #loop tofetch the directory and file names by slicing the 512 bytes to 32 bytes
                for val in range(self.BytsPerSec//32):
                    #slicing 32 bytes
                    sector_data_32=sector_data_512[start:end]
                    #checking the zero,first and 11 th sector to identify the directory
                    if(sector_data_32[0]==0x2e and sector_data_32[1]==0x20 and sector_data_32[11] ==0x10):
                        #appending the value to a list
                        if(len(self.dir_folder_list)>0):
                            self.dir_folder['set'+str(set)]=self.dir_folder_list
                            self.dir_folder_list={}
                            set+=1
                        self.dir_folder_list['dir'+str(dir)]=sector_data_32[:8].decode('utf-8')
                        dir+=1
                    #checking the 11 th and 12 th byte to identify the files
                    if(sector_data_32[11]==0x20 and sector_data_32[12]==0x00):
                        #slicing the first 11 bytes to get the file name 
                        self.dir_folder_list['file'+str(file)]=sector_data_32[:11].decode(('utf-8'))
                        #slicing 26 and 27 byte to get the starting cluster of the file 
                        self.start_cluster[int.from_bytes(sector_data_32[26:28],byteorder='little')]=sector_data_32[:11].decode(('utf-8'))
                        #slicing the 28 byte till 32 byte to get the size of the file
                        self.file_size[sector_data_32[:11].decode(('utf-8'))]=int.from_bytes(sector_data_32[28:],byteorder='little')
                        file+=1
                    start=end
                    end=end+32 
        if(len(self.dir_folder_list)>0):
            self.dir_folder['set'+str(set)]=self.dir_folder_list
        print('\n')
        print('------------------------Files and directories details are gathered---------------')
        #calling function to get chain of clusters where the data is store for the files in FAT table
        cluster_chain=self.getchainofcluster()
        #calling the function to read the chain of clusters and get the contents of each file
        self.getfilecontent(cluster_chain)
        #function to create the recovered directories ad files
        self.file_creation()
    #function to get the chain of cluster where the data is stored for each file using start of cluster
    def getchainofcluster(self):
        #initializing dictionary to store chain of cluster
        chain_of_cluster={}
        #iterating through the fat table to get the chain of clusters
        for key,value in self.start_cluster.items():
            #setting the fat offset from FATStart
            fat_table_offset=self.FATStart*self.BytsPerSec
            #assigning the start cluster as the cluster value
            cluster_value=key
            #initializing an empty list to store the cluster chain for the respective files
            chain_of_cluster[value]=[]
            #checking if the cluster_value is less than the 0xFFF8 which indicates the last cluster in file (0xFFF8-0xFFFF)
            while cluster_value < 0xFFF8:
                #appending the cluster chain values
                chain_of_cluster[value].append(cluster_value)
                #calculating the cluster sector by multiplying cluster_value *2 becasue each cluster value occupies 2 bytes
                cluster_sector=fat_table_offset+(cluster_value*2)
                self.fat.seek(cluster_sector)
                #reading only 2 bytes of data to get next cluster number becasue each cluster value occupies 2 bytes
                cluster_data=self.fat.read(2)
                next_cluster_num=struct.unpack("<H",cluster_data)[0]
                #assigning the next_cluster number as current_cluster
                cluster_value=next_cluster_num
        print("\n")
        print("------------------chain of cluster details for the data of coreesponding files are gathered---------------")
        return chain_of_cluster
    #funnction to get the file content with the chain of cluster values obtained
    def getfilecontent(self,cluster_chain):
        #initializing variables
        self.file_content={}
        #iterating through the cluster of chain to get the data for a particular file
        for key,value in cluster_chain.items():
            file_data=b''
            #iterating through the list to get data from each cluster for a file
            for cluster in value:
                #calculating cluster_offset to seek the values
                cluster_offset=self.FirstDataSector+(cluster-2)*(self.SecPerClus)
                self.fat.seek(cluster_offset*self.BytsPerSec)
                #reading 4 sector data because  1 cluster has four sectors
                cluster_data=self.fat.read(self.BytsPerSec*self.SecPerClus)
                file_data+=cluster_data
            #after concatinating, decoding the value using ascii
            self.file_content[key]=file_data.decode('ascii')
        print("\n")
        print("------------------The contents of the files are gathered using chain of cluster---------------------------")
    #function to create the Recoveredfiles and Goodfiles
    def file_creation(self):
        #using counter for file ames format
        counter=1
        #creating the directory RecoveredFiles which has list of folders and .BIN and txt files inside the folders
        os.mkdir('RecoveredFiles')
        #iterating through the file and directory names to create BIN and txt files
        for key,value in self.dir_folder.items():
            for key,value in value.items():
                #creating the folder
                if('dir' in key ):
                    os.mkdir('RecoveredFiles'+'/'+key)
                    dir_name=key
                #creating the files inside the folder
                else:
                    #for the format FILENAME0001.BIN and FILENAME0001.TXT using format
                    filename='FILE'+str('{:04d}'.format(counter))
                    #creating the recovered files in bin format which are of incorrect length 
                    file_bin=open('RecoveredFiles'+'/'+dir_name+'/'+filename+'.BIN','w')
                    file_bin.write(self.file_content[value])
                    file_bin.close()
                    #creating the recovered files in txt format which are trimmed using strip()
                    file_txt=open('RecoveredFiles'+'/'+dir_name+'/'+filename+'.TXT','w')
                    file_txt.write(self.file_content[value].strip('\x00'))
                    file_txt.close()
                    counter+=1
        print("\n")
        print("--------------------RecoveredFiles folder is created with recovered .BIN and .TXT files-------------------")
        #creating the directory GoodFiles which has listing.txt and recovered files of correctname and length 
        os.mkdir('GoodFiles')
        listing_file_content=''
        #iterating through the list of corresponding files in a directory and content of files 
        for key,value in self.dir_folder.items():
            for key,value in value.items():
                #storing the directory values and file values in a string 
                if('dir' in key):
                    listing_file_content+=(key+','+ value +'-->'+'\n')
                else:
                    listing_file_content+=(value +', '+ 'file_size :'+ str(self.file_size[value]))+'\n'
        #creating new file listing.txt to append the string with directory and file details
        file_list=open('GoodFiles/listing.txt','w')

        file_list.write(listing_file_content)
        file_list.close()
        print("\n")
        print("--------------------GoodFiles folder is created with listing.txt and .TXT files with correct names-------------------")
        #iterating through the files to create .TXT files with correctname 
        for key,value in self.dir_folder.items():
            for key,value in value.items():
                if('dir' in key ):
                    os.mkdir('GoodFiles'+'/'+key)
                    dir_name=key
                else:
                    filename_txt=open('GoodFiles'+'/'+dir_name+'/'+value+'.TXT','w')
                    #files are trimmed using strip()
                    filename_txt.write(self.file_content[value].strip('\x00'))
                    filename_txt.close()
                    counter+=1
        print("\n")
        print("--------------------GoodFiles folder is created with listing.txt and .TXT files with correct names-------------------")
#main function to call the FAT class
if __name__ == '__main__':
    #path of the disk image which is corrupted
    fatimageFile='/home/bhaskarb/h-drive/My Desktop/SCC 443 - Digital Forensics/Coding - Python/SCC443-Assignment(python)/Python files/fat16-36298529-34.img'
    #creating obj of the FAT class and passing the disk image to the init function 
    fat_obj=FAT(fatimageFile)
