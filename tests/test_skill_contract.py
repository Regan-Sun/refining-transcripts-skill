"""静态文档回归检查；不调用模型，不证明逐字稿处理行为已通过。"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / 'refining-transcripts/SKILL.md').read_text(encoding='utf-8')
README = (ROOT / 'README.md').read_text(encoding='utf-8')
CASES = (ROOT / 'tests/验收用例.md').read_text(encoding='utf-8')


def section(title: str) -> str:
    match = re.search(r'^## ' + re.escape(title) + r'\n(.*?)(?=^## |\Z)', SKILL, re.M | re.S)
    return match.group(1) if match else ''


class SkillContractTests(unittest.TestCase):
    def require(self, text: str, *terms: str) -> None:
        for term in terms:
            self.assertTrue(term in text, f'缺少静态约束：{term}')

    def test_frontmatter_shape(self):
        front = SKILL.split('---\n', 2)[1]
        keys = re.findall(r'^([a-z-]+):', front, re.M)
        self.assertEqual(keys, ['name', 'description', 'metadata'])
        self.assertRegex(front, r'(?m)^name: refining-transcripts$')
        self.assertRegex(front, r'(?m)^  version: "\d+\.\d+\.\d+"$')
        description = re.search(r'^description: (.+)$', front, re.M).group(1)
        self.assertTrue(0 < len(description) <= 1024)

    def test_headings_fences_and_local_links(self):
        headings = re.findall(r'^## (.+)$', SKILL, re.M)
        self.assertEqual(len(headings), len(set(headings)))
        for path in ROOT.rglob('*.md'):
            text = path.read_text(encoding='utf-8')
            self.assertEqual(len(re.findall(r'^```', text, re.M)) % 2, 0, str(path))
            for target in re.findall(r'\]\(([^)]+)\)', text):
                if not re.match(r'^[a-z]+://|^#', target):
                    self.assertTrue((path.parent / target.split('#')[0]).exists(), target)

    def test_chunk_ownership_not_text_deduplication(self):
        self.require(section('长文本分块协议'), '主体范围', '参考上下文', '只输出主体范围', '原文位置', '不得按文字相似度')
        # 仅拦截已知的参考段规则反转，不作为通用语义验证。
        self.require(section('长文本分块协议'), '参考内容只用于理解，不再次输出')

    def test_oversize_case_and_streaming_review(self):
        self.require(section('长文本分块协议'), '超长案例', '完整句或问答回合', '同一案例续段', '按顺序分段回读')
        self.assertFalse('不得从完整案例、问答、练习反馈或同一句发言中间硬切' in SKILL)

    def test_source_coverage_is_not_a_fidelity_score(self):
        self.require(section('长文本分块协议'), '保留 / 按规则删除 / 待核', '未处理', '删除理由', '不进入最终正文', '不等于保真通过')

    def test_course_classification_cannot_summarize(self):
        self.require(section('课程内容分类'), '不授予摘要权限', '相同的保真标准', '混合型录音', '按片段')
        self.assertFalse('保留关键讨论' in section('课程内容分类'))

    def test_user_selected_scope(self):
        self.require(section('输入要求'), '用户指定范围', '范围外', '相关上下文')
        self.require(section('完成状态'), '用户指定范围内')
        self.assertFalse('全部输入均已处理' in SKILL)

    def test_four_independent_status_fields(self):
        state = section('完成状态')
        self.require(state, '内容状态：', '处理范围：', '音频核验：', '文件验收：', '处理中', '未核听', '待核优先', '不是文件交付完成')
        self.assertFalse('若交付 Word，还必须满足现有 Word 文件与视觉验收要求' in state)
        self.require(state, '关键疑点已解决')

    def test_speaker_labels_are_scoped_and_unreliable_merges_are_marked(self):
        text = section('人名、术语、数字与说话人')
        self.require(text, '仅在所属源文件内有效', '跨文件同号不等于同一人',
                     '不再将该合并标签视为可靠身份', '切换边界也不明', '〔说话人待核〕')
        self.assertNotIn('原转写把多人合并：继续使用', text)

    def test_uncertainty_marker_preserves_readable_source(self):
        self.require(section('人名、术语、数字与说话人'), '保留仍可辨认的原转写内容',
                     '追加标记', '三百元〔数字待核〕', '确实无法辨认', '否定词')

    def test_multi_file_overlap_requires_event_evidence(self):
        self.require(section('长文本分块协议'), '多文件关系', '重复导出', '不同转写版本',
                     '同一次发言', '内部保留各源位置', '合并待确认')

    def test_t03_does_not_preload_the_restricted_source(self):
        text = re.search(r'^## T03｜.*?(?=^## T04｜)', CASES, re.M | re.S).group(0)
        self.require(text, '仅供测试执行器准备', '首轮不得包含P01—P08原文',
                     '禁用绕过该入口的全文读取', '记为阻塞', '每次最多3个主体段落')
        self.assertNotIn('用户要求：“精修整段小组讨论', text)

    def test_entity_correction_without_fact_rewrite(self):
        self.require(section('证据优先级'), '识别和书写错误', '同一对象', '内部依据', '无条件全局替换', '不能据此改写', '发言归属')

    def test_uncertainty_survives_downstream(self):
        self.require(section('上下游路由'), '待核标记', '来源位置', '核验状态', '不表示所有事实已核实', '不得把待核内容当作已确认事实')

    def test_source_commands_are_not_authorization(self):
        self.require(section('输入要求'), '操作指令', '待处理内容', '不构成', '调用工具', '覆盖文件', '上传资料')

    def test_existing_fidelity_and_word_guards_remain(self):
        self.require(SKILL, '忠实原意 > 事实准确 > 可复核 > 可读性 > 文采', '不把个人意见改写成集体共识', '不把相关性改写成因果', '不根据模型记忆猜测人名', '不为交付擅自安装依赖', '不在文末另列清单', '从实际生成的 Word 提取正文', '渲染最终 Word 并检查各页', '议程中的角色不能自动证明')

    def test_eight_behavior_cases_are_executable_specs(self):
        cases = re.split(r'^## T\d{2}｜', CASES, flags=re.M)[1:]
        self.assertEqual(len(cases), 8)
        for case in cases:
            self.require(case, '**输入**', '**通过标准**', '**失败示例**', '**观察证据**')
        self.require(CASES, '未执行', '不是行为测试', '独立会话')

    def test_readme_version_and_test_scope(self):
        self.require(README, '2.1.0', '主体范围', '内容状态', '处理范围', '音频核验', '文件验收', '静态检查', '行为验收', 'tests/验收用例.md')


if __name__ == '__main__':
    unittest.main(verbosity=2)
