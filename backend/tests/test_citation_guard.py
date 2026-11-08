from agent.citation_guard import strip_unsupported_citations
from structlog.testing import capture_logs

LAW_CONTEXT = (
    "Άρθρο 72 – Εγγυήσεις. Η εγγύηση καλής εκτέλεσης ορίζεται σε ποσοστό 4%.\n"
    "Άρθρο 132 – Τροποποίηση συμβάσεων κατά τη διάρκειά τους."
)
CONTRACT_CONTEXT = (
    "Άρθρο 4 – Τίμημα. Το συνολικό τίμημα ανέρχεται σε 48.000 ευρώ.\n"
    "Άρθρο 7 – Ποινικές ρήτρες. Σύμφωνα με το άρθρο 72 του Ν. 4412/2016."
)


def test_citation_in_context_is_kept():
    answer = "Σύμφωνα με το άρθρο 72 του Ν. 4412/2016, η εγγύηση είναι 4%."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == answer


def test_inflected_and_unaccented_forms_match_the_context():
    answer = "Η τροποποίηση διέπεται από τις διατάξεις του αρθρου 132 και του ΑΡΘΡΟΥ 72."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == answer


def test_contract_articles_from_contract_chunks_are_kept():
    answer = "Το τίμημα ορίζεται στο Άρθρο 4 της Σύμβασης. Βλ. Άρθρα 4 και 7."
    assert strip_unsupported_citations(answer, CONTRACT_CONTEXT) == answer


def test_text_without_citations_is_unchanged():
    answer = "Η εγγύηση καλής εκτέλεσης ανέρχεται σε 4% (Ν. 4412/2016), για 12 μήνες."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == answer


def test_unsupported_parenthetical_citation_is_dropped():
    answer = (
        "Ανατρέξτε στο σχετικό τμήμα του Ν. 4412/2016 (π.χ. άρθρα 360-366 περί ΑΕΠΠ) "
        "ή ανεβάστε το σχετικό έγγραφο."
    )
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == (
        "Ανατρέξτε στο σχετικό τμήμα του Ν. 4412/2016 ή ανεβάστε το σχετικό έγγραφο."
    )


def test_range_with_only_one_number_in_context_is_removed():
    context = "Άρθρο 360 – Προδικαστική προσφυγή."
    answer = "Για τις προθεσμίες δείτε στο Ν. 4412/2016, π.χ. άρθρα 360–366."
    assert (
        strip_unsupported_citations(answer, context) == "Για τις προθεσμίες δείτε στο Ν. 4412/2016."
    )


def test_range_fully_in_context_is_kept():
    context = "Τα άρθρα 360-366 ρυθμίζουν την προδικαστική προσφυγή."
    answer = "Η προσφυγή ρυθμίζεται από το άρθρο 362."
    assert strip_unsupported_citations(answer, context) == answer


def test_list_with_one_unsupported_number_is_removed_as_a_whole():
    answer = "Βλ. άρθρα 72 και 207. Η εγγύηση είναι 4%."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == "Η εγγύηση είναι 4%."


def test_citation_after_article_keeps_the_sentence_grammatical():
    answer = "Σύμφωνα με το άρθρο 207 παρ. 1 του Ν. 4412/2016, η προθεσμία είναι 10 ημέρες."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == (
        "Σύμφωνα με το σχετικό άρθρο του Ν. 4412/2016, η προθεσμία είναι 10 ημέρες."
    )


def test_genitive_and_plural_citations_keep_agreement():
    answer = "Η εφαρμογή του άρθρου 207 και των άρθρων 360-366 απαιτεί προσοχή."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == (
        "Η εφαρμογή του σχετικού άρθρου και των σχετικών άρθρων απαιτεί προσοχή."
    )


def test_text_stays_readable_after_removal():
    answer = (
        "Η προδικαστική προσφυγή δεν καλύπτεται από τα διαθέσιμα αποσπάσματα "
        "(βλ. άρθρο 360). Προτείνεται να ανατρέξετε στο πλήρες κείμενο του νόμου, "
        "π.χ. άρθρα 360-366, ή στην ΕΑΑΔΗΣΥ."
    )
    result = strip_unsupported_citations(answer, LAW_CONTEXT)
    assert result == (
        "Η προδικαστική προσφυγή δεν καλύπτεται από τα διαθέσιμα αποσπάσματα. "
        "Προτείνεται να ανατρέξετε στο πλήρες κείμενο του νόμου, ή στην ΕΑΑΔΗΣΥ."
    )
    assert "  " not in result and "()" not in result and " ," not in result


def test_removal_is_logged_with_the_article_numbers():
    with capture_logs() as logs:
        strip_unsupported_citations("Δείτε τα άρθρα 72 και 207.", LAW_CONTEXT)
    assert logs == [
        {
            "event": "unsupported_article_citation_removed",
            "log_level": "info",
            "citation": "τα άρθρα 72 και 207",
            "articles": [72, 207],
            "missing": [207],
        }
    ]


def test_supported_citation_is_not_logged():
    with capture_logs() as logs:
        strip_unsupported_citations("Βλ. άρθρο 72.", LAW_CONTEXT)
    assert logs == []


# ── Emphasis around removed citations ────────────────────────────────────────


def _no_orphan_markers(text: str) -> bool:
    return not any(m in text for m in ("****", "** **", "__ __", "* *", "  ", " .", " ,"))


def test_citation_alone_in_bold_drops_the_pair():
    answer = "Η προθεσμία είναι 10 ημέρες **Άρθρο 999**. Ισχύει για όλους."
    result = strip_unsupported_citations(answer, LAW_CONTEXT)
    assert result == "Η προθεσμία είναι 10 ημέρες. Ισχύει για όλους."
    assert _no_orphan_markers(result)


def test_citation_in_bold_after_article_keeps_grammar_and_bold():
    answer = "Ισχύει σύμφωνα με το **Άρθρο 999**."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == (
        "Ισχύει σύμφωνα με το **σχετικό Άρθρο**."
    )


def test_prefixed_citation_in_bold_is_removed_like_plain_text():
    answer = "Δείτε π.χ. το **άρθρο 999**."
    plain = "Δείτε π.χ. το άρθρο 999."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == "Δείτε."
    assert strip_unsupported_citations(plain, LAW_CONTEXT) == "Δείτε."


def test_citation_at_start_of_bold_phrase():
    answer = "**Άρθρο 999 του Ν.4412/2016**: η προθεσμία είναι 10 ημέρες."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == (
        "**του Ν.4412/2016**: η προθεσμία είναι 10 ημέρες."
    )
    answer = "**Άρθρο 999: η εγγύηση είναι 4%** σε κάθε σύμβαση."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == (
        "**η εγγύηση είναι 4%** σε κάθε σύμβαση."
    )


def test_citation_at_end_of_bold_phrase():
    answer = "**Η εγγύηση ορίζεται σε 4%, Άρθρο 999**. Επόμενη πρόταση."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == (
        "**Η εγγύηση ορίζεται σε 4%**. Επόμενη πρόταση."
    )


def test_two_citations_in_one_bold_span_keep_the_supported_one():
    for answer in (
        "Δείτε **Άρθρο 72 και Άρθρο 999** για λεπτομέρειες.",
        "Δείτε **Άρθρο 999 και Άρθρο 72** για λεπτομέρειες.",
        "Δείτε **Άρθρο 72, Άρθρο 999** για λεπτομέρειες.",
    ):
        assert strip_unsupported_citations(answer, LAW_CONTEXT) == (
            "Δείτε **Άρθρο 72** για λεπτομέρειες."
        ), answer


def test_italic_and_bold_italic_citations():
    assert (
        strip_unsupported_citations("Δείτε *Άρθρο 999* για λεπτομέρειες.", LAW_CONTEXT)
        == "Δείτε για λεπτομέρειες."
    )
    assert strip_unsupported_citations("Δείτε ***Άρθρο 999*** τώρα.", LAW_CONTEXT) == "Δείτε τώρα."
    assert strip_unsupported_citations(
        "Η εφαρμογή του *άρθρου 999* απαιτεί προσοχή.", LAW_CONTEXT
    ) == ("Η εφαρμογή του *σχετικού άρθρου* απαιτεί προσοχή.")


def test_bold_citation_inside_parentheses_drops_the_parenthetical():
    answer = "Η εγγύηση είναι 4% (**Άρθρο 999**) για 12 μήνες."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == "Η εγγύηση είναι 4% για 12 μήνες."


def test_neighbouring_emphasis_that_still_wraps_text_is_untouched():
    answer = "**Προσοχή** Άρθρο 999 **σημαντικό**."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == "**Προσοχή** **σημαντικό**."


def test_bold_citation_as_list_item_label():
    answer = "* **Άρθρο 999**: Η εγγύηση είναι 4%.\n- Άρθρο 999, η προθεσμία.\n1. Τέλος."
    assert strip_unsupported_citations(answer, LAW_CONTEXT) == (
        "* Η εγγύηση είναι 4%.\n- η προθεσμία.\n1. Τέλος."
    )


def test_lines_without_removals_come_back_byte_identical():
    untouched = [
        "Σύμφωνα με το **Άρθρο 72** του Ν. 4412/2016,  η εγγύηση είναι 4% .",
        "* **Σημείωση**: *ισχύει*  ** ** όπως __ήδη__ αναφέρθηκε.",
    ]
    answer = "\n".join([untouched[0], "Δείτε **Άρθρο 999** για λεπτομέρειες.", untouched[1]])
    lines = strip_unsupported_citations(answer, LAW_CONTEXT).split("\n")
    assert lines == [untouched[0], "Δείτε για λεπτομέρειες.", untouched[1]]
    for line in untouched:
        assert strip_unsupported_citations(line, LAW_CONTEXT) == line
