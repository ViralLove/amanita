"""
Network Graph Exporter для SpiralEngine.
Exports activation graph to JSON для visualization.

Usage:
    from bot.tests.utils.network_exporter import NetworkExporter
    
    exporter = NetworkExporter(spiral_engine_contract)
    output_file = exporter.export_graph()
    print(f"Exported to: {output_file}")
"""

import os
import json
from datetime import datetime
from pathlib import Path


class NetworkExporter:
    """Exports SpiralEngine activation graph to JSON"""
    
    def __init__(self, contract):
        self.contract = contract
    
    def export_graph(self, output_file='bot/tests/data/activation_graph.json'):
        """
        Export full activation graph to JSON.
        Format compatible with D3.js, NetworkX, Gephi.
        
        Returns:
            str: Path to exported file
        """
        print("📊 Exporting network graph...")
        
        # Get all users
        all_users = self._get_all_users()
        
        # Get network name from environment (dynamic)
        network_name = os.getenv('BLOCKCHAIN_PROFILE', 'localhost')
        
        # Build graph structure
        graph = {
            'metadata': {
                'total_nodes': len(all_users) + 1,  # +1 для deployer
                'exported_at': datetime.now().isoformat(),
                'contract': 'SpiralEngine',
                'network': network_name,
                'exporter_version': '1.0'
            },
            'nodes': [],
            'edges': [],
            'communities': []
        }
        
        # Add deployer as root
        deployer = os.getenv('DEPLOYER_ADDRESS')
        if not deployer:
            raise RuntimeError("DEPLOYER_ADDRESS not found in environment")
        
        self._add_node(graph, deployer, generation=0)
        
        # Add all activated users
        for user_addr in all_users:
            generation = self._calculate_generation(user_addr, deployer)
            self._add_node(graph, user_addr, generation)
            
            # Add edge (activator → user)
            activator = self.contract.functions.userActivator(user_addr).call()
            if activator != '0x0000000000000000000000000000000000000000':
                self._add_edge(graph, activator, user_addr)
        
        # Update max generation in metadata
        if graph['nodes']:
            graph['metadata']['max_generation'] = max(n['generation'] for n in graph['nodes'])
        else:
            graph['metadata']['max_generation'] = 0
        
        # Detect organic trust communities (по gen 1 branches)
        self._add_communities(graph, deployer)
        
        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(graph, f, indent=2)
        
        print(f"✅ Exported: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
        print(f"   Communities: {len(graph['communities'])}")
        print(f"   File: {output_file}")
        
        return str(output_path.resolve())
    
    def _get_all_users(self):
        """Get all activated users from contract"""
        all_users = []
        
        try:
            # Method 1: Try getAllActivatedUsers() if exists
            all_users = self.contract.functions.getAllActivatedUsers().call()
        except AttributeError:
            # Method 2: Iterate through public activatedUsers array
            try:
                i = 0
                while True:
                    user = self.contract.functions.activatedUsers(i).call()
                    all_users.append(user)
                    i += 1
            except Exception:
                pass  # Reached end of array
        
        return all_users
    
    def _add_node(self, graph, address, generation):
        """Add node with metadata"""
        try:
            circle = self.contract.functions.getCircleMembers(address).call()
        except Exception:
            circle = []
        
        graph['nodes'].append({
            'id': address,
            'generation': generation,
            'circleSize': len(circle),
            'circleFilled': len(circle) >= 12,
            'capacity': 12 - len(circle),
            'label': f"Gen{generation}-{address[:8]}"
        })
    
    def _add_edge(self, graph, from_addr, to_addr):
        """Add directed edge (activation relationship)"""
        graph['edges'].append({
            'from': from_addr,
            'to': to_addr,
            'type': 'activation'
        })
    
    def _add_communities(self, graph, deployer):
        """
        Detect organic trust communities.
        Each community = activator + их circle (activatedBy).
        """
        try:
            gen1_users = self.contract.functions.getCircleMembers(deployer).call()
        except Exception:
            gen1_users = []
        
        # Root community (deployer + gen1)
        if gen1_users:
            graph['communities'].append({
                'id': 'root',
                'type': 'organic_trust',
                'leader': deployer,
                'members': [deployer] + gen1_users,
                'size': len(gen1_users) + 1,
                'generation': 0
            })
        
        # Branch communities (each gen1 + их circle)
        for i, gen1_user in enumerate(gen1_users):
            try:
                circle = self.contract.functions.getCircleMembers(gen1_user).call()
                
                if len(circle) > 0:
                    graph['communities'].append({
                        'id': f'branch_{i+1}',
                        'type': 'organic_trust',
                        'leader': gen1_user,
                        'members': [gen1_user] + circle,
                        'size': len(circle) + 1,
                        'generation': 1
                    })
            except Exception:
                continue  # Skip if can't get circle
    
    def _calculate_generation(self, user_addr, root):
        """
        Calculate generation level via recursive parent lookup.
        Generation 0 = root (deployer)
        Generation 1 = direct activations by root
        Generation 2 = activations by gen 1, etc.
        """
        if user_addr.lower() == root.lower():
            return 0
        
        try:
            activator = self.contract.functions.userActivator(user_addr).call()
            
            if activator == '0x0000000000000000000000000000000000000000':
                return 999  # No activator (shouldn't happen)
            
            parent_gen = self._calculate_generation(activator, root)
            return parent_gen + 1
            
        except Exception:
            return 999  # Unknown generation
    
    def get_network_stats(self):
        """
        Get current network statistics without full export.
        Quick summary для reporting.
        """
        all_users = self._get_all_users()
        deployer = os.getenv('DEPLOYER_ADDRESS')
        
        try:
            gen1_users = self.contract.functions.getCircleMembers(deployer).call()
        except:
            gen1_users = []
        
        # Count communities (deployer + non-empty gen1 circles)
        communities_count = 1 if gen1_users else 0  # Root
        
        for gen1_user in gen1_users:
            try:
                circle = self.contract.functions.getCircleMembers(gen1_user).call()
                if len(circle) > 0:
                    communities_count += 1
            except:
                continue
        
        # Calculate max generation
        max_gen = 0
        for user in all_users:
            try:
                gen = self._calculate_generation(user, deployer)
                if gen < 999:
                    max_gen = max(max_gen, gen)
            except:
                continue
        
        return {
            'total_nodes': len(all_users) + 1,  # +1 for deployer
            'total_edges': len(all_users),  # Each user has 1 activator
            'total_users': len(all_users),
            'max_generation': max_gen,
            'communities': communities_count,
            'gen1_size': len(gen1_users),
            'deployer_circle_filled': len(gen1_users) >= 12
        }

