
import random
import sys
import hashlib
import string


def sha1(password):
    password = str(password).encode('utf-8')
    dk = hashlib.pbkdf2_hmac('sha1', password, b'salt', 10)
    return(dk.hex())


def add_file(points, point, file_name):
    point.files.append(file_name)
    guid = sha1(file_name)
    target_point, path = search(points, point, guid, traverse_all=False)
    target_point.info.guids.append(guid)

    for e in path:
        e.info.file_ref[guid] = point


def add_files(points, count):
    files = []
    for i in range(count):
        file_name = ''.join(random.sample(
            string.ascii_letters, random.randint(1, 20)))
        files.append(file_name)
        current_point = random.choice(points)
        add_file(points, current_point, file_name)

    return files


def search(points, start_point, guid, traverse_all=True):
    current_prefix = -1
    current_point = start_point
    path = [current_point]

    while not current_point.conteins_G(guid):
        max_prefix = get_max_prefix(current_point.G, guid)
        if len(max_prefix) <= current_prefix:
            break
        if max_prefix not in current_point.info.pref_table:
            break

        current_prefix = len(max_prefix)
        scores = [len(get_max_prefix(e.G, guid))
                  for e in current_point.info.pref_table[max_prefix]]
        i = scores.index(max(scores))
        current_point = current_point.info.pref_table[max_prefix][i]
        path.append(current_point)

    if (not current_point.conteins_G(guid)) and traverse_all:
        q = [current_point]
        used = set()
        pref = get_max_prefix(current_point.G, guid)

        while q:
            current_point = q[0]
            q = q[1:]
            if current_point.conteins_G(guid):
                break

            for cpref in [e for e in current_point.info.pref_table.keys() if len(e) >= len(pref)]: 
                for p in current_point.info.pref_table.get(cpref, []):
                    if p not in used:
                        q.append(p)
                        used.add(p)

    return current_point, path


def add_connection(graph, point_max, point):
    k = 0
    while k == 0:
        random_point = random.choice(list(graph.keys()))
        if len(graph[random_point]) == point_max or point in graph[random_point] or point == random_point:
            continue
        else:
            k = 1
            if point in graph:
                graph[point].append(random_point)
                graph[random_point].append(point)
            else:
                graph[random_point].append(point)
                graph[point] = [random_point]


class Point(object):

    def __init__(self, ID):
        self.ID = ID
        self.G = sha1(self.ID)
        self.files = []
        self.info = INFO()

    def __repr__(self):
        return "<" + self.G + ", " + str(self.ID) + ">"

    def conteins_G(self, guid):
        if self.G == guid or guid in self.info.guids:
            return True
        return False


class INFO:
    def __init__(self):
        self.guids = []
        self.pref_table = dict()
        self.file_ref = dict()


def get_max_prefix(G1, G2):
    k = -1
    for i in range(len(G1)):
        if G1[i] == G2[i]:
            k += 1
        else:
            break
    if k == -1:
        return ''
    else:
        return G1[0:k+1]


def generate_logic_graph(graph, c_max):

    points = list(graph.keys())
    for i in range(len(points)):
        for j in range(i):
            prefix = get_max_prefix(points[i].G, points[j].G)

            t = points[i].info.pref_table.get(prefix, [])
            if len([e for e in t if e.G[:len(prefix)+1][-1] == points[j].G[:len(prefix)+1][-1] ]) < c_max:
                t.append(points[j])
                points[i].info.pref_table[prefix] = t

            t = points[j].info.pref_table.get(prefix, [])
            if len([e for e in t if e.G[:len(prefix)+1][-1] == points[i].G[:len(prefix)+1][-1] ] ) < c_max:
                t.append(points[i])
                points[j].info.pref_table[prefix] = t


def generate_graph(point_count: int, point_min: int, point_max: int):

    points = [Point(i) for i in range(point_count)]
    graph = dict()

    graph[points[0]] = [points[1]]
    graph[points[1]] = [points[0]]

    for i in range(2, point_count):
        add_connection(graph, point_max, points[i])

    for point in points:
        connections_count = random.randint(point_min, point_max)
        if len(graph[point]) < connections_count:
            for j in range(connections_count - len(graph[point])):
                add_connection(graph, point_max, point)
        else:
            continue
    return graph



def make_metric(stat):
        return f'min: {min(stat)}; max: {max(stat)}; mean: {sum(stat)/len(stat)}'



def find_route_len(graph, node, tnode):
    cp = []
    sp = None
    used = set([node])
    q = [node]

    layer_rest = 1
    next_layer_rest = 0
    l = 0
    while q:
        cn = q[0]
        q = q[1:]
        layer_rest -= 1

        if cn == tnode:
            return l

        for n in graph[cn]:
            if n in used:
                continue
            used.add(n)
            q.append(n)
            next_layer_rest += 1
        
        if layer_rest == 0:
            l +=1
            layer_rest = next_layer_rest
            next_layer_rest = 0

def test1(graph, points, files):
    alg_path_len = []
    ip_path_len = []
    for e in random.sample(files, 100):
        point = random.choice(points)
        guid = sha1(e)
        last_point, path = search(points, point, guid)
        if e in last_point.files:
            target_point = last_point
        else:
            target_point = last_point.info.file_ref[guid]
            path.append(target_point)
        if e not in target_point.files:
            raise Exception('file not found')
        
        alg_path_len.append(len(path)-3)
        ip_path_len.append(find_route_len(graph, point, target_point))
    
    return alg_path_len, ip_path_len

random.seed(10)
graph = generate_graph(1000, 3, 9)
generate_logic_graph(graph, 1)
points = list(graph.keys())
files = add_files(points, 1000)

algstat, ipstat = test1(graph, points, files)

print(f'tapestry: {make_metric(algstat)}')
print(f'ip : {make_metric(ipstat)}')

filestat = [len(p.info.guids) for p in points]
filerefstat = [len(p.info.file_ref) for p in points]

print(f'file keys per node : {make_metric(filestat)}')
print(f'file refs per node : {make_metric(filerefstat)}')

