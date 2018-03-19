import rpyc
from pathlib import Path
import threading
import datetime

heart_dict = {}

class NameNode(rpyc.Service):

    def __init__(self, a):
        self.file_to_block = "./file_to_block.txt"
        self.block_to_node = "./block_to_node.txt"
        self.valid_nodes = "./valid_nodes.txt"
        self.maintenance_needed = "./maintenance_needed.txt"

        my_file = self.file_to_block
        my_file_path = Path(my_file)
        if not my_file_path.is_file():
            open_my_file = open(my_file, 'w')
            open_my_file.close()
        
        my_file = self.block_to_node
        my_file_path = Path(my_file)
        if not my_file_path.is_file():
            open_my_file = open(my_file, 'w')
            open_my_file.close()

        my_file = self.valid_nodes
        my_file_path = Path(my_file)
        if not my_file_path.is_file():
            open_my_file = open(my_file, 'w')
            open_my_file.close()

        my_file = self.maintenance_needed
        my_file_path = Path(my_file)
        if not my_file_path.is_file():
            open_my_file = open(my_file, 'w')
            open_my_file.close()


        self.replication_factor = 3
        self.block_size = 134217728
        self.default_time = 10
        self.interval = 6.0
        self.replication_interval = 120.0

    def exposed_list_directory(self, directory_path, file_paths):
        # Adds string file paths to given file_path empty set;
        # if invalid path, returns False, otherwise True

        # Truncates any appended "/"
        if directory_path[-1] == "/":
            directory_path = directory_path[0:-1]

        directory_level = len(directory_path.split("/"))
        directory_exists = False

        my_file = open(self.file_to_block)

        for line_of_text in my_file:
            current_path = line_of_text.split(",")[0]
            path_level = len(current_path.split("/"))

            if directory_path == current_path:
                directory_exists = True

            # only including paths ONE directory level lower
            if ((directory_path + "/") == current_path[0:len(directory_path) + 1]) \
                    & (path_level == (directory_level + 1)):
                file_paths.append(current_path)

        my_file.close()
        return directory_exists

    def exposed_create_directory(self, directory_path):

        # Truncates any appended "/"
        if directory_path[-1] == "/":
            directory_path = directory_path[0:-1]

        new_directory = directory_path.split("/")[-1]
        len_new_directory = len(new_directory)
        existing_directory = directory_path[0:-(len_new_directory + 1)]

        success = False
        if existing_directory == "":
            success = True
        read_file_to_block = open(self.file_to_block)
        for line_of_text in read_file_to_block:
            current_directory = line_of_text.split(",")[0]
            if current_directory == existing_directory:
                success = True
            if current_directory == directory_path:
                success = False
        read_file_to_block.close()

        if success:
            write_file_to_block = open(self.file_to_block, "a+")
            write_file_to_block.write(directory_path + ", {}\n")
            write_file_to_block.close()

        return success

    def exposed_make_file(self, file_size, file_path):
        # Check all directories as you go; only read once
        if file_size % self.block_size == 0:
            num_blocks = file_size / self.block_size
        else:
            num_blocks = (file_size / self.block_size) + 1

        print("Starting make file")
        file_name = file_path.split("/")[-1]
        len_file_name = len(file_name)
        recent_directory = file_path[0:-(len_file_name + 1)]

        success = False
        if recent_directory == "":
            success = True
        read_file_to_block = open(self.file_to_block)
        for line_of_text in read_file_to_block:
            current_directory = line_of_text.split(",")[0]
            if current_directory == recent_directory:
                success = True
            if current_directory == file_path:
                success = False
        read_file_to_block.close()

        return_blocks = []

        print("Ending make file")
        if success:
            print("returning")
            return_stuff = self.write_assigned_blocks_to_file(num_blocks, return_blocks, file_path)
            print(return_stuff)
            #return self.write_assigned_blocks_to_file(num_blocks, return_blocks, file_path)
            return return_stuff

    def write_assigned_blocks_to_file(self, num_blocks, return_blocks, file_path):        
        write_block_to_node = open(self.block_to_node, "a+")
        write_file_to_block = open(self.file_to_block, "a+")
        write_file_to_block.write(file_path + ",{")
        
        assign_nodes = self.get_open_location(num_blocks, [])
        node_iterator = 0
        
        for i in range(int(num_blocks)):
            partition = "part-" + str(i)
            name = file_path + "/" + partition
            return_blocks.append(name)
            new_blocks = ""
            print ("iterating ", i)
            for j in range(self.replication_factor):
                if j == 0:
                    new_blocks = new_blocks + assign_nodes[node_iterator]
                    node_iterator = node_iterator + 1
                else:
                    new_blocks = new_blocks + "," + assign_nodes[node_iterator]
                    node_iterator = node_iterator + 1
            return_blocks.append("{" + new_blocks + "}")
            
            if i == 0:
                write_file_to_block.write(partition)
            else:
                write_file_to_block.write("," + partition)
            write_block_to_node.write(name + ", {}\n")
        
        write_file_to_block.write("}\n")
        write_file_to_block.close()
        write_block_to_node.close()

        return return_blocks

    def get_open_location(self, num_blocks, dont_include):
        nodes = self.make_node_dictionary()
        top_nodes = []
        copy_index_min = 0
        copy_index_max = 0
        for i in range(int(self.replication_factor * num_blocks)):
            appended_node = False
            if i % self.replication_factor == 0:
                copy_index_min = i
                copy_index_max = i
            while not appended_node:
                open_node = min(nodes.keys(), key=(lambda k: nodes[k]))
                if (open_node not in top_nodes[copy_index_min:(copy_index_max + 1)]) and open_node not in dont_include:
                    top_nodes.append(open_node)
                    copy_index_max = copy_index_max + 1
                    appended_node = True
                nodes[open_node] = nodes[open_node] + 1

        return top_nodes

    def exposed_read_file(self, path, path_list):
        file_list = self.find_all_files(path)
        if not file_list:
            return 0
        block_file = open(self.file_to_block, 'r')
        block_list = []
        for each_line in block_file:
            current_path = each_line.split(",")[0]
            if current_path == path:
                ending_list = each_line.split("{")[1]
                ending_list = ending_list.split("}")[0]
                ending_list = ending_list.split(",")
                for ending in ending_list:
                    if not (ending == ""):
                        block_list.append(path + "/" + ending)
        block_file.close()
        print(block_list)
        node_file = open(self.block_to_node, 'r')
        for each_line in node_file:
            current_block = each_line.split(",")[0]
            if current_block in block_list:
                print("block found", current_block)
                path_list.append(each_line.strip("\n"))
        node_file.close()
        return 1

    def exposed_receive_block_report(self, node_id, block_list):
        response = ""
        node_id = str(node_id)
        my_file = open(self.valid_nodes, 'r')
        lines = my_file.readlines()
        my_file.close()
        if not ((node_id + "\n") in lines):
            self.new_node(node_id)
            response = "delete,*"
            return response
        heart_dict[node_id] = self.default_time
        my_file = open(self.maintenance_needed, 'r')
        lines = my_file.readlines()
        my_file.close()
        my_file = open(self.maintenance_needed, 'w')
        for each_line in lines:
            each_line.strip("\n")
            line_breakdown = each_line.split(",")
            if line_breakdown[0] == node_id:
                if not response == "":
                    response = response + ","
                response = response + "forward," + line_breakdown[1] + "," + line_breakdown[2]
            else:
                my_file.write(each_line + "\n")
        my_file.close()
        for block in block_list:
            found = 0
            my_file = open(self.block_to_node, 'r')
            lines = my_file.readlines()
            my_file.close()
            my_file = open(self.block_to_node, 'w')
            for each_line in lines:
                if (each_line.split(",")[0] == block):
                    found = 1
                    node_list = each_line.split("{")[1]
                    node_list = node_list.split("}")[0]
                    node_list = node_list.split(",")
                    new_line = each_line.split("{")[0] + "{"
                    if not(node_id in node_list):
                        for node in node_list:
                            if node != "":
                                new_line = new_line + node + ","
                        new_line = new_line + node_id
                        new_line = new_line + "}\n"
                        my_file.write(new_line)
                    else:
                        my_file.write(each_line)
                else:
                    my_file.write(each_line)
            if found == 0:
                response = response + "delete," + block + ","
            my_file.close()
        return response
    
    def new_node(self, node_id):
        my_file = open(self.valid_nodes, 'r')
        lines = my_file.readlines()
        my_file.close()
        if node_id in lines:
            return 0
        my_file = open(self.valid_nodes, 'a+')
        my_file.write(node_id)
        my_file.write("\n")
        my_file.close()
        heart_dict[node_id] = self.default_time
        return 1
    
    def heart_check(self):
        print(heart_dict)
        for node, value in heart_dict.items():   
            if value > 0:
                value = value - 1
            heart_dict[node] = value
            if value == 0:
                self.dead_node(node)
                heart_dict.pop(node, None)
    
            
    def dead_node(self, node_id):
        my_file = open(self.valid_nodes, 'r')
        lines = my_file.readlines()
        my_file.close()
        my_file = open(self.valid_nodes, 'w')
        for each_line in lines:
            if not (each_line == str(node_id) + "\n"):
                my_file.write(each_line)
        my_file.close()
        my_file = open(self.block_to_node, 'r')
        lines = my_file.readlines()
        my_file.close()
        my_file = open(self.block_to_node, "w")
        for each_line in lines:
            node_list = each_line.split("{")[1]
            node_list = node_list.split("}")[0]
            node_list = node_list.split(",")
            if node_id in node_list:
                new_line = each_line.split("{")[0] + "{"
                first = 0
                for node in node_list:
                    if not (node == node_id):
                        if first == 0:
                            new_line = new_line + node
                            first = 1
                        else:
                            new_line = new_line + "," + node
                new_line = new_line + "}\n"
                my_file.write(new_line)
            else:
                my_file.write(each_line)
            my_file.close()

    def find_all_files(self, path):
        in_path = path
        my_file = open(self.file_to_block, 'r')
        file_list = []
        path_length = len(in_path)
        if in_path[path_length - 1] == "/":
            in_path = in_path[0:path_length - 1]
            path_length = path_length - 1
        directory_level = len(in_path.split("/"))
        for each_line in my_file:
            current_path = each_line.split(",")[0]
            if current_path == in_path:
                file_list.append(current_path)
            else:
                path_level = len(current_path)
                if ((in_path + "/") == current_path[0:path_length + 1]) \
                        & (path_level == directory_level + 1):
                    file_list.append(current_path)
        my_file.close()
        return file_list

    def exposed_delete_path(self, path):
        file_list = self.find_all_files(path)
        if not file_list:
            success = 0
            return success
        my_file = open(self.file_to_block, 'r')
        lines = my_file.readlines()
        my_file.close()
        my_file = open(self.file_to_block, 'w')
        block_list = []
        for each_line in lines:
            if each_line.split(",")[0] in file_list:
                block_list.append(each_line)
            else:
                my_file.write(each_line)
        my_file.close()
        if block_list:
            my_file = open(self.block_to_node, 'r')
            lines = my_file.readlines()
            my_file.close()
            my_file = open(self.block_to_node, 'w')
            for each_line in lines:
                block = each_line.split(",")[0]
                if not (block.startswith(path)):
                    my_file.write(each_line)
            my_file.close()
        success = 1
        return success

    def replication_check(self):
        print("checking replication factor " + str(datetime.datetime.now()).split('.')[0] + "\n\n")
        read_block_to_node = open(self.block_to_node)

        problem_lines = []
        for line_of_text in read_block_to_node:
            if line_of_text != "\n":
                node_list = line_of_text.split("{")[1]
                node_list = node_list.split("}")[0]
                if len(node_list) > 0:
                    node_list = node_list.split(",")
                    block_name = line_of_text.split(",")[0]
                    num_replicas = len(node_list)
                    node_with_data = node_list[0]
                    if num_replicas == 1:
                        problem_lines.append((2, node_with_data, block_name, (node_list[0])))
                        print(problem_lines[-1])
                    elif num_replicas == 2:
                        problem_lines.append((1, node_with_data, block_name, (node_list[0], node_list[1])))
                        print(problem_lines[-1])
        read_block_to_node.close()

        my_file = open(self.maintenance_needed, "a+")
        for (num_missing, contact_node, block, present_nodes) in problem_lines:
            forward_nodes = self.get_open_location(float(num_missing) / self.replication_factor, present_nodes)
            print(str(contact_node) + "," + block + "," + str(forward_nodes).replace('[', "").split("]")[0])    
            my_file.write(str(contact_node) + "," + block + "," + str(forward_nodes).replace('[', "").replace("'", "").split("]")[0] + "\n")

        my_file.close()
        return

    def make_node_dictionary(self):
        print ("make node dictionary called")
        nodes = dict()
        read_block_to_node = open(self.block_to_node)
        for line_of_text in read_block_to_node:
            if line_of_text != "\n":
                node_list = line_of_text.split("{")[1]
                node_list = node_list.split("}")[0]
                if len(node_list) > 0:
                    node_list = node_list.split(",")
                    nodes[node_list[0]] = nodes.get(node_list[0], 0) + 1
                    if len(node_list) > 1:
                        nodes[node_list[1]] = nodes.get(node_list[1], 0) + 1
                        if len(node_list) > 2:
                            nodes[node_list[2]] = nodes.get(node_list[2], 0) + 1
        read_block_to_node.close()

        my_file = open(self.valid_nodes)
        for line_of_text in my_file:
            if (line_of_text not in nodes.keys()) & (line_of_text != "\n"):
                nodes[line_of_text.strip("\n").strip(" ")] = 0
        my_file.close()
        return nodes

    def heartbeat_timer(self):
        threading.Timer(self.interval, self.heartbeat_timer).start()
        self.heart_check()

    def replication_timer(self):
        threading.Timer(self.replication_interval, self.replication_timer).start()
        self.replication_check()


def main():


    """
    #list_directory testing
    sample_directory_path = "/Users/isabellebutterfield/"
    #sample_current_path = "/Users/isabellebutterfield"
    #print(sample_directory_path + "/")
    #print(sample_current_path[0:len(sample_directory_path) + 1])
    sample_path_list = []
    directory_set = list_directory(sample_directory_path, sample_path_list)
    for path in sample_path_list:
        print(path)

    #create_directory testing
    create_directory("/Users/isabellebutterfield/SUFS")

    #get_open_location testing
    print(get_open_location(3,2))
    """
    # print(make_file(128, "/Users/isabellebutterfield/test.txt"))
    # print(make_file(256, "/Users/isabellebutterfield/test2.txt"))
    # node = NameNode()

    from rpyc.utils.server import ThreadedServer
    name_node = NameNode("")
    name_node.heartbeat_timer()
    name_node.replication_timer()
    t = ThreadedServer(NameNode, port=5000)
    t.start()

    #print(node.make_file(10, "/Users/isabellebutterfield/test7.txt"))
    #node.replication_check()

    ############################################################

    # HI NANCY!!
    # Here's an example of what you'll get from calling make_file(256, "/Users/isabellebutterfield/test2.txt")
    # ['/Users/isabellebutterfield/test2.txt/part-0', '{3, 2, 4}', '/Users/isabellebutterfield/test2.txt/part-1', '{1, 3, 5}', '/Users/isabellebutterfield/test2.txt/part-2', '{2, 4, 1}', '/Users/isabellebutterfield/test2.txt/part-3', '{3, 5, 2}']

    ############################################################

if __name__ == '__main__':
    main()


