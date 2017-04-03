from flametree import file_tree
import matplotlib.pyplot as plt
from Bio import SeqIO
from dna_features_viewer import BiopythonTranslator
import pandas
from collections import defaultdict

from ..Filter import NoRestrictionSiteFilter
from ..AssemblyMix import RestrictionLigationMix
from .plots import (name_fragment, plot_cuts, plot_assembly_graph,
                    AssemblyTranslator)

def full_assembly_report(parts, target, enzyme="BsmBI", max_assemblies=40,
                         fragments_filters='auto',
                         assemblies_prefix='assembly'):
    """Write a full assembly report in a folder or a zip.

    Parameters
    ----------

    parts
      List of Biopython records representing the parts, potentially on entry
      vectors. All the parts provided should have different attributes ``name``
      as it is used to name the files.

    target
      Either a path to a folder, or to a zip file, or ``@memory`` to return
      a string representing

    """
    if (len(set(p.name for p in parts)) < len(parts)):
        raise ValueError("All parts provided should have different names")
    if fragments_filters == 'auto':
        fragments_filters = [NoRestrictionSiteFilter(enzyme)]

    report = file_tree(target, replace=True)
    provided_parts_dir = report._dir("provided_parts")
    fragments_dir = report._dir("fragments")
    graph_dir = report._dir("assembly_graph")
    assemblies_dir = report._dir("assemblies")

    mix = RestrictionLigationMix(parts, enzyme)

    # PROVIDED PARTS

    for part in parts:
        linear = part.linear if hasattr(part, 'linear') else False
        ax, gr = plot_cuts(part, enzyme, linear=linear)
        f = provided_parts_dir._file(part.name + ".pdf").open('wb')
        ax.figure.savefig(f, format='pdf', bbox_inches="tight")
        plt.close(ax.figure)
        gb_file = provided_parts_dir._file(part.name + ".gb")
        SeqIO.write(part, gb_file, 'genbank')

    # FRAGMENTS

    seenfragments = defaultdict(lambda *a: 0)
    for fragment in mix.fragments:
        gr = BiopythonTranslator().translate_record(fragment)
        ax, pos = gr.plot()
        name = name_fragment(fragment)
        seenfragments[name] += 1
        file_name = "%s_%02d.pdf" % (name, seenfragments[name])
        ax.figure.savefig(fragments_dir._file(file_name).open('wb'),
                          format='pdf', bbox_inches="tight")
        plt.close(ax.figure)

    # GRAPH

    ax, graph = plot_assembly_graph(mix, fragments_filters=fragments_filters)
    ax.figure.savefig(graph_dir._file('graph.pdf').open('wb'),
                      format='pdf', bbox_inches='tight')
    data = [
        dict(
            end_1=end_1, end_2=end_2,
            parts=" & ".join([name_fragment(f)
                              for f in data["fragments"]])
        )
        for end_1, end_2, data in graph.edges(data=True)
    ]
    df = pandas.DataFrame.from_records(data,
                                       columns=['end_1', 'end_2', 'parts'])
    df.to_csv(graph_dir._file('parts_per_slot.csv'), index=False)
    plt.close(ax.figure)

    # ASSEMBLIES
    assemblies = mix.compute_circular_assemblies(
        fragments_filters=fragments_filters)
    assemblies_data = []
    for i, asm in zip(range(max_assemblies), assemblies):
        name = '%s_%02d' % (assemblies_prefix, (i+1))
        assemblies_data.append(dict(
            name=name,
            parts=" & ".join([name_fragment(f) for f in asm.fragments]),
            number_of_parts=len(asm.fragments),
            assembly_size=len(asm)
        ))
        SeqIO.write(asm, assemblies_dir._file(name + '.gb').open('w'),
                    'genbank')
        gr_record = AssemblyTranslator().translate_record(asm)
        ax, gr = gr_record.plot(figure_width=16)
        ax.set_title(name)
        ax.figure.savefig(assemblies_dir._file(name + '.pdf').open('wb'),
                          format='pdf', bbox_inches='tight')
        plt.close(ax.figure)
    df = pandas.DataFrame.from_records(
        assemblies_data,
        columns=['name', 'number_of_parts', 'assembly_size', 'parts']
    )
    df.to_csv(report._file('report.csv'), index=False)
    n_constructs = len(df)
    if target == '@memory':
        return n_constructs, report._close()
    else:
        return n_constructs
