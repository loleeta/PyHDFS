# PyHDFS
Python parody of Apache Hadoop Distributed File System (see design overview [here](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)). Uses AWS [EC2](https://aws.amazon.com/ec2/) for server communication, and [S3](https://aws.amazon.com/s3/) for persistent storage.

## Architecture 
### `name_node`
The NameNode master server manages the namespace of the file system and mediates access to clients.

### `data_node`
The DataNode facilitates storage and retrieval of files, which are internally split into blocks (128 MB) and replicated up to a factor of 3. 

## Dependencies
```
- rpyc
- boto
- S3Handler
```
