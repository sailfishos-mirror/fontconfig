/* Copyright (C) 2026 fontconfig Authors */
/* SPDX-License-Identifier: HPND */

#include "fcint.h"
#if ENABLE_FREETYPE
#  include "fontconfig/fcfreetype.h"
#endif
#if ENABLE_FONTATIONS
#  include "fontconfig/fcfontations.h"
#endif

/* Public */
unsigned int
FcIndexerQueryAll (const FcChar8 *file,
                   unsigned int   id,
                   int           *count,
                   FcFontSet     *set)
{
    unsigned int (*query_func) (const FcChar8 *, unsigned int, FcBlanks *, int *, FcFontSet *) =
#if ENABLE_FONTATIONS && !defined(ENABLE_FREETYPE)
	FcFontationsQueryAll;
#elif ENABLE_FREETYPE
	FcFreeTypeQueryAll;
#endif

#if ENABLE_FONTATIONS
    if (getenv ("FC_FONTATIONS") != NULL) {
	query_func = FcFontationsQueryAll;
    }
#endif
    return query_func (file, id, NULL, count, set);
}

FcPattern *
FcIndexerQuery (const FcChar8 *file,
                unsigned int   id,
                int           *count)
{
    FcFontSet *set = FcFontSetCreate();
    FcPattern *ret = NULL;

    if (!FcIndexerQueryAll (file, id, count, set))
	goto bail;
    if (set->nfont > 0) {
	ret = set->fonts[0];
	FcPatternReference (ret);
    }

bail:
    FcFontSetDestroy (set);

    return ret;
}

#define __fcindex__
#include "fcaliastail.h"
#undef __fcindex__
