import itertools
import networkx as nx
from ...Fragment.StickyEndFragment import StickyEndFragment
from ...AssemblyMix import (
    StickyEndAssemblyMix,
    RestrictionLigationMix,
    AssemblyMixError,
)
from ..AssemblySimulation import AssemblySimulation
from ..AssemblyFlaw import AssemblyFlaw
from ..Assembly import Assembly


class BASICAssembly(Assembly):
    def simulate_adapters_assembly(self, records):
        original_part = records[1]
        mix = RestrictionLigationMix(
            records,
            enzymes=["BsaI"],
            name="%s_adapters_ligation" % original_part.id,
        )
        adapter_fragments = []
        for fragment_index, fragment in mix.fragments_dict.items():
            left_end = str(fragment.seq.left_end)
            right_end = str(fragment.seq.right_end)
            if max(len(left_end), len(right_end)) > 4:
                adapter_fragments.append(fragment_index)
        if len(adapter_fragments) != 4:  # Two "ends" and their complements
            error = AssemblyFlaw(
                message="Two many fragments have a long overhang",
                data={"parts": [r.id for r in records]},
            )
            return AssemblySimulation(errors=[error], mixes=(mix,))
        graph = mix.connections_graph
        constructs = []
        for start, end in itertools.product(adapter_fragments, repeat=2):
            if end == start:
                continue
            if nx.has_path(graph, start, end):
                path = nx.shortest_path(graph, start, end)
                fragments = [mix.fragments_dict[i] for i in path]
                score = sum([f.is_reversed for f in fragments])
                construct = StickyEndFragment.assemble(
                    fragments, circularize=False
                )
                constructs.append((score, construct))
        if len(constructs) != 2:  # A linear assembly and its complement
            error = AssemblyFlaw(
                message="Two many possible ligations",
                data={"parts": [r.id for r in records]},
            )
            return mix, error
        _, construct = sorted(constructs)[0]
        construct.id = "%s_with_adapters" % original_part.id
        construct.original_part = original_part
        return construct

    def simulate(self, sequence_repository, annotate_parts_homologies=True):

        parts = sequence_repository.get_records(self.parts)
        L = len(parts)
        if L % 3:
            error = AssemblyFlaw(
                assembly=self,
                message="The number of parts for BASIC assembly should be"
                "a multiple of 3",
            )
            return AssemblySimulation(
                assembly=self,
                sequence_repository=sequence_repository,
                errors=[error],
            )

        # ANNEAL PARTS AND ADAPTERS SEPARATELY

        adapted_part_records = []
        errors, warnings = [], []
        part_triplets = [parts[i : i + 3] for i in range(0, L, 3)]
        for triplet in part_triplets:
            simulation = self.simulate_adapters_assembly(triplet)
            if isinstance(simulation, StickyEndFragment):
                adapted_part_records.append(simulation)
            else:
                mix, error = simulation
                return AssemblySimulation(
                    assembly=self,
                    sequence_repository=sequence_repository,
                    errors=[error],
                    mixes=(mix,),
                )
        if len(errors):
            return AssemblySimulation(
                assembly=self,
                sequence_repository=sequence_repository,
                errors=errors,
            )

        # MIX ALL ADAPTED PARTS

        mix = StickyEndAssemblyMix(
            name="%s_BASIC_mix" % self.name, fragments=adapted_part_records
        )
        generator = mix.compute_circular_assemblies(
            annotate_parts_homologies=annotate_parts_homologies
        )
        construct_records = sorted(
            [asm for (i, asm) in zip(range(self.max_constructs), generator)],
            key=lambda asm: str(asm.seq),
        )
        self.attribute_ids_to_constructs(construct_records)
        found = len(construct_records)
        self._detect_constructs_number_error(found, errors)
        self._detect_max_constructs_reached(found, warnings)

        return AssemblySimulation(
            assembly=self,
            construct_records=construct_records,
            mixes=(mix,),
            errors=errors,
            sequence_repository=sequence_repository,
        )

