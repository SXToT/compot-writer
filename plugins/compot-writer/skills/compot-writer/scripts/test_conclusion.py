from __future__ import annotations

import unittest

from build_package import validate_conclusion


VALID_BODY = (
    "该研究围绕复杂环境下成像质量下降的问题，提出结合内部与外部对比学习的恢复方法，"
    "并通过多组真实场景实验和定量指标验证了结构设计的有效性与稳定性，"
    "为后续视觉任务获得更可靠的输入提供了可复用的技术路径和实验依据"
)


class ConclusionTests(unittest.TestCase):
    def test_preferred_summary_is_accepted(self) -> None:
        conclusion = f"综上，{VALID_BODY}。"
        self.assertEqual(validate_conclusion(conclusion), conclusion)

    def test_supported_alternative_is_accepted(self) -> None:
        conclusion = f"总体而言，{VALID_BODY}。"
        self.assertEqual(validate_conclusion(conclusion), conclusion)

    def test_missing_summary_cue_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_conclusion(f"该研究最终表明，{VALID_BODY}。")

    def test_too_short_summary_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_conclusion("综上，该方法有效。")

    def test_missing_final_full_stop_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_conclusion(f"综上，{VALID_BODY}")


if __name__ == "__main__":
    unittest.main()
