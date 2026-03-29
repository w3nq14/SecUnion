import networkx as nx

class GraphBuilder:
    def build(self, crawl_data):
        G = nx.DiGraph()

        # 先添加所有节点
        node_ids = {node['id'] for node in crawl_data['nodes']}
        for node_id in node_ids:
            G.add_node(node_id)

        # 只添加两端都存在的边
        for edge in crawl_data['edges']:
            if edge['source'] in node_ids and edge['target'] in node_ids:
                G.add_edge(edge['source'], edge['target'])

        # Calculate metrics
        nodes = []
        for node in G.nodes():
            in_degree = G.in_degree(node)
            out_degree = G.out_degree(node)
            nodes.append({
                "id": node,
                "label": self._extract_domain(node),
                "in_degree": in_degree,
                "out_degree": out_degree,
                "degree": in_degree + out_degree
            })

        edges = [{"source": e[0], "target": e[1]} for e in G.edges()]

        return {"nodes": nodes, "edges": edges}

    def _extract_domain(self, url):
        return url.split('/')[2]
