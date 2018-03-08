import rpyc
import pickle
from reply import Reply
from io import BytesIO
import shutil

block_size = 2048
data_node_IP = 'localhost'

#create blocks from file
def create_blocks(file_name):
    blocks_to_send = []
    with open(file_name, 'rb') as input:
        bytes = input.read()
        for i in range(0, len(bytes), block_size):
            blocks_to_send.append(bytes[i: i+block_size])
    print("Created chunks:", len(blocks_to_send))
    return blocks_to_send

#sending a file over
def send_block(file_name):
    conn = rpyc.connect(data_node_IP, 5000, config={'allow_public_attrs': True})
    print("Connecting with server...")

    data_node = conn.root.BlockStore()
    file_blocks = create_blocks(file_name)

    i = 1
    for block in file_blocks:
        block_id = 'MobyBlock' + str(i)
        print("Now inserting: ", block_id)
        reply = Reply.Load(data_node.put_block(block_id, block))
        print(reply.status)

        if reply.is_err():
            print('Could not insert block', block_id)
            print(reply.err)
            break
        i+=1

#retrieve blocks and save blocks to a file
def get_blocks(block_name, new_file_name):
    conn = rpyc.connect(data_node_IP, 5000,
                        config={'allow_public_attrs': True})
    data_node = conn.root.BlockStore()
    print("Connecting with server...")

    reply = Reply.Load(data_node.get_block(block_name))

    if reply.is_err():
        print('Could not get block ', block_name)
        print(reply.err)

    fetched_bytes = BytesIO()
    fetched_bytes.write(reply.result)

    fetched_bytes.flush()
    fetched_bytes.seek(0)
    print('Fetched: ', len(fetched_bytes.getbuffer()))

    print("Saving to: ", new_file_name)
    with open(new_file_name, 'wb') as dest:
        shutil.copyfileobj(fetched_bytes, dest, block_size)
    dest.close()

#test get block report here (func in name node)
def get_block_report():
    conn = rpyc.connect(data_node_IP, 5000,
                        config={'allow_public_attrs': True})
    data_node = conn.root
    print("Connecting with server...")


if __name__ == '__main__':
    print()
    #send blocks
    # print('Testing: save blocks in storage')
    # print('Sending Moby Dick...')
    # send_block('mobydick.txt')
    # print("Send complete")

    #retrieve block
    # print('Testing: retrieving block')
    # get_blocks('MobyBlock1', 'MobyBlock1.txt')
    # print('Retrieval complete')

    #print blocks

    #delete block