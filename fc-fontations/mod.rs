/*
 * fontconfig/fc-fontations/mod.rs
 *
 * Copyright 2025 Google LLC.
 *
 * Permission to use, copy, modify, distribute, and sell this software and its
 * documentation for any purpose is hereby granted without fee, provided that
 * the above copyright notice appear in all copies and that both that
 * copyright notice and this permission notice appear in supporting
 * documentation, and that the name of the author(s) not be used in
 * advertising or publicity pertaining to distribution of the software without
 * specific, written prior permission.  The authors make no
 * representations about the suitability of this software for any purpose.  It
 * is provided "as is" without express or implied warranty.
 *
 * THE AUTHOR(S) DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
 * INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO
 * EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY SPECIAL, INDIRECT OR
 * CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
 * DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
 * TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
 * PERFORMANCE OF THIS SOFTWARE.
 */

extern crate fc_fontations_bindgen;
extern crate font_types;
extern crate read_fonts;
extern crate skrifa;

mod names;
mod pattern_bindings;

use names::add_names;

use fc_fontations_bindgen::{
    fcint::{
        FC_COLOR_OBJECT, FC_FONTFORMAT_OBJECT, FC_FONT_HAS_HINT_OBJECT, FC_OUTLINE_OBJECT,
        FC_SCALABLE_OBJECT,
    },
    FcFontSet, FcFontSetAdd, FcPattern,
};

use font_types::Tag;
use pattern_bindings::{FcPatternBuilder, PatternElement};
use std::str::FromStr;

use read_fonts::{
    FileRef::{self, Collection, Font},
    FontRef, TableProvider,
};

use std::{
    ffi::{CStr, CString, OsStr},
    iter::IntoIterator,
    os::unix::ffi::OsStrExt,
};

#[no_mangle]
/// Externally called in fcfontations.c as the file scanner function
/// similar to the job that FreeType performs.
///
/// # Safety
/// * At this point, the font file path is not dereferenced.
/// * In this initial sanity check mock call, only one empty pattern
///   is added to the FontSet, which is null checked, which is sound.
pub unsafe extern "C" fn add_patterns_to_fontset(
    font_file: *const libc::c_char,
    font_set: *mut FcFontSet,
) -> libc::c_int {
    let font_path = unsafe { OsStr::from_bytes(CStr::from_ptr(font_file).to_bytes()) };
    let bytes = std::fs::read(font_path).ok().unwrap_or_default();
    let fileref = FileRef::new(&bytes).ok();

    let fonts = fonts_and_indices(fileref);
    for (font, ttc_index) in fonts {
        for pattern in build_patterns_for_font(&font, font_file, ttc_index) {
            if FcFontSetAdd(font_set, pattern) == 0 {
                return 0;
            }
        }
    }

    1
}

fn fonts_and_indices(
    file_ref: Option<FileRef>,
) -> impl Iterator<Item = (FontRef<'_>, Option<i32>)> {
    let (iter_one, iter_two) = match file_ref {
        Some(Font(font)) => (Some((Ok(font.clone()), None)), None),
        Some(Collection(collection)) => (
            None,
            Some(
                collection
                    .iter()
                    .enumerate()
                    .map(|entry| (entry.1, Some(entry.0 as i32))),
            ),
        ),
        None => (None, None),
    };
    iter_two
        .into_iter()
        .flatten()
        .chain(iter_one)
        .filter_map(|(font_result, index)| {
            if let Ok(font) = font_result {
                return Some((font, index));
            }
            None
        })
}

fn has_one_of_tables<I>(font_ref: &FontRef, tags: I) -> bool
where
    I: IntoIterator,
    I::Item: ToString,
{
    tags.into_iter().fold(false, |has_tag, tag| {
        let tag = Tag::from_str(tag.to_string().as_str());
        if let Ok(tag_converted) = tag {
            return has_tag | font_ref.data_for_tag(tag_converted).is_some();
        }
        has_tag
    })
}

fn has_hint(font_ref: &FontRef) -> bool {
    if has_one_of_tables(font_ref, ["fpgm", "cvt "]) {
        return true;
    }

    if let Some(prep_table) = font_ref.data_for_tag(Tag::new(b"prep")) {
        return prep_table.len() > 7;
    }
    false
}

fn build_patterns_for_font(
    font: &FontRef,
    _: *const libc::c_char,
    _: Option<i32>,
) -> Vec<*mut FcPattern> {
    let mut pattern = FcPatternBuilder::new();

    add_names(font, &mut pattern);

    let has_glyf = has_one_of_tables(font, ["glyf"]);
    let has_cff = has_one_of_tables(font, ["CFF ", "CFF2"]);
    let has_color = has_one_of_tables(font, ["COLR", "SVG ", "CBLC", "SBIX"]);

    // Color and Outlines
    let has_outlines = has_glyf | has_cff;

    pattern.append_element(PatternElement::new(
        FC_OUTLINE_OBJECT as i32,
        has_outlines.into(),
    ));
    pattern.append_element(PatternElement::new(
        FC_COLOR_OBJECT as i32,
        has_color.into(),
    ));
    pattern.append_element(PatternElement::new(
        FC_SCALABLE_OBJECT as i32,
        (has_outlines || has_color).into(),
    ));
    pattern.append_element(PatternElement::new(
        FC_FONT_HAS_HINT_OBJECT as i32,
        has_hint(font).into(),
    ));

    match (has_glyf, has_cff) {
        (_, true) => {
            pattern.append_element(PatternElement::new(
                FC_FONTFORMAT_OBJECT as i32,
                CString::new("CFF").unwrap().into(),
            ));
        }
        _ => {
            pattern.append_element(PatternElement::new(
                FC_FONTFORMAT_OBJECT as i32,
                CString::new("TrueType").unwrap().into(),
            ));
        }
    }

    pattern
        .create_fc_pattern()
        .map(|p| p.into_raw() as *mut FcPattern)
        .into_iter()
        .collect()
}

#[cfg(test)]
mod test {
    use crate::add_patterns_to_fontset;
    use fc_fontations_bindgen::{FcFontSetCreate, FcFontSetDestroy};
    use CString;

    #[test]
    fn basic_pattern_construction() {
        unsafe {
            let font_set = FcFontSetCreate();
            assert!(add_patterns_to_fontset(CString::new("").unwrap().into_raw(), font_set) == 1);
            FcFontSetDestroy(font_set);
        }
    }
}
