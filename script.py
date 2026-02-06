# -*- coding: utf-8 -*-
import os
import fontforge
import psMat
import datetime
# ================= 配置区 =================
# 主字体（英文/代码），决定行高和基准宽度
MONO_PATH = "IBMPlexMono-Regular.ttf"
# 副字体（中文），用于补充汉字
SC_PATH = "IBMPlexSansSC-Regular.ttf"
# 输出文件名
OUTPUT_PATH = "out/PlexMono-SC.ttf"

# 中文缩放比例
# 0.9 是一個经验值，防止中文太大撑开行高或显得突兀
SCALE_FACTOR = 0.90 
# =========================================

def main():
    print("Opening fonts...")
    mono = fontforge.open(MONO_PATH)
    sc = fontforge.open(SC_PATH)

    # 1. 获取 Mono 的标准宽度 (通常是字符 'M' 或空格的宽度)
    # Plex Mono Regular 通常是 600 (在 1000 em 下)
    mono_width = mono[ord('M')].width
    target_cjk_width = mono_width * 2
    
    print(f"Mono width: {mono_width}")
    print(f"Target CJK width: {target_cjk_width}")

    # 2. 调整 SC 的 Em Size 以匹配 Mono
    sc.em = mono.em

    # 3. 选中 SC 中的中文字符范围
    # 这里主要选取 CJK Unified Ideographs (4E00-9FFF)
    # 你也可以根据需要添加扩展区 A (3400-4DBF) 等
    print("Selecting CJK glyphs from Source...")
    sc.selection.none()
    sc.selection.select(("ranges", None), 0x4E00, 0x9FFF)
    
    # 还可以选上中文标点 (3000-303F)，但要小心覆盖掉 Mono 的符号
    # 这里为了安全，我们只选 3000-303F 中确实是中文特有的
    sc.selection.select(("ranges", "more"), 0x3000, 0x303F)

    # 4. 对选中的中文进行缩放 (以中心为原点)
    print(f"Scaling CJK glyphs by {SCALE_FACTOR}...")
    # 获取选中字符的迭代器
    for glyph in sc.selection.byGlyphs:
        # 缩放
        glyph.transform(psMat.scale(SCALE_FACTOR))
        
        # 5. 强制调整宽度并居中
        # 现在的 glyph 可能宽度不一，我们需要强制设为 2倍宽
        # 并把字形轮廓居中放置
        
        # 计算当前内容的边界
        bbox = glyph.boundingBox()
        glyph_content_width = bbox[2] - bbox[0]
        
        # 计算居中所需的左边距 (Left Side Bearing)
        # (目标宽度 - 内容宽度) / 2 - 原本的左边界偏移
        new_lsb = (target_cjk_width - glyph_content_width) / 2 - bbox[0]
        
        # 应用变换：先移动，再设宽度
        glyph.transform(psMat.translate(new_lsb, 0))
        glyph.width = target_cjk_width

    # 6. 复制并合并到 Mono
    print("Copying and Pasting into Mono...")
    sc.copy()
    mono.selection.none()
    mono.selection.select(("ranges", None), 0x4E00, 0x9FFF)
    mono.selection.select(("ranges", "more"), 0x3000, 0x303F)
    # merge 模式会自动保留 Mono 原有的字（如果冲突），只填补空缺
    mono.paste()

    # 7. 修改字体元数据 (防止安装冲突)
    print("Updating metadata...")
    mono.fontname = "PlexMonoSC-Regular"
    mono.fullname = "Plex Mono SC Regular"
    mono.familyname = "Plex Mono SC"
    today_str = datetime.datetime.now().strftime("%Y.%m.%d")
    mono.version = "Version " + today_str

    # 8. 生成文件
    print(f"Generating {OUTPUT_PATH}...")
    out_dir = os.path.dirname(OUTPUT_PATH)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    mono.generate(OUTPUT_PATH)
    print("Done!")

if __name__ == "__main__":
    main()
