"""
"""

from copy import copy

from Bio import Restriction


from ..biotools import annotate_record, autoselect_enzyme
from ..StickyEndsSeq import StickyEndsSeqRecord
from .AssemblyMixBase import AssemblyMixBase

class RestrictionLigationMix(AssemblyMixBase):

    def __init__(
        self,
        parts=None,
        enzymes=None,
        fragments=None,
        fragments_filters=(),
        name=None
    ):
        # shallow copy seems sufficient and problem-free.
        # deepcopy would be safer but it is a computational bottleneck.
        self.parts = copy(parts) if parts else parts
        self.fragments = copy(fragments) if fragments else fragments
        if enzymes is not None:
            enzymes = [Restriction.__dict__[e] for e in enzymes]
        self.enzymes = enzymes
        self.fragments_filters = fragments_filters
        self.name = name
        self.initialize()
    
    def compute_digest(self, part):
        """Compute the fragments resulting from the digestion"""
        return StickyEndsSeqRecord.list_from_record_digestion(
            part, self.enzymes
        )

    def compute_fragments(self):
        """Compute the (sticky-ended) fragments resulting from the digestion of
        the mix's parts by the mix's enzyme.

        Note that all fragments receive an annotation (feature) of type
        "source" that will show in the genbank of final constructs.
        """
        self.fragments = []
        for part in self.parts:
            for fragment in self.compute_digest(part):
                # print (fragment)
                if not isinstance(fragment, StickyEndsSeqRecord):
                    continue
                fragment.original_part = part
                annotate_record(
                    fragment,
                    feature_type="misc_feature",
                    source=part.id,
                    note="From " + part.id,
                )
                self.fragments.append(fragment)

    @staticmethod
    def assemble(fragments, circularize=False, annotate_homologies=False):
        """Assemble sticky-end fragments into a single one (sticky or not).

        Parameters
        ----------

        fragments
          List of StickyEndsSeqRecord fragments

        circularize
          If True and if the two ends of the final assembly are compatible,
          circularize the construct, i.e. return a non-sticky record
          representing the circular assembly of the fragments.

        annotate_homologies
          If True, all homology regions that where formerly sticky ends will
          be annotated in the final record.
        """
        return StickyEndsSeqRecord.assemble(
            fragments,
            circularize=circularize,
            annotate_homologies=annotate_homologies,
        )

    @staticmethod
    def will_clip_in_this_order(fragment1, fragment2):
        """Return True iff f1's right sticky end fits f2's left."""
        return fragment1.will_clip_in_this_order_with(fragment2)
