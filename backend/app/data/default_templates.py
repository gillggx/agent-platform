"""Default workflow templates"""

STANDARD_SPEC_TEMPLATE = {
    "workflow": {
        "id": "standard-spec",
        "name": "標準 Spec 流程",
        "description": "PM 雙人對話起草 → Architect 技術審核（可退回 PM）→ QA 審核並產出 Checklist（可退回 PM）→ Director 最終審批",
        "version": 2,
        "steps": [
            # ── Step 1: PM 雙人對話，起草初版 Spec ──────────────────────────
            {
                "id": "pm_dialogue",
                "agent_role": "pm",
                "task_type": "dialogue",
                "config": {
                    "min_rounds": 2,
                    "max_rounds": 3,
                },
                "depends_on": [],
                "routing": {
                    "type": "static",
                    "next_steps": ["architect_review"]
                }
            },
            # ── Step 2: Architect 審核技術可行性，產出技術規格 ───────────────
            {
                "id": "architect_review",
                "agent_role": "architect",
                "task_type": "review",
                "depends_on": ["pm_dialogue"],
                "routing": {
                    "type": "llm_decision",
                    "decision_prompt": (
                        "根據 Architect 文件最末的決策標記判斷路由：\n"
                        "- 若包含 **決策：APPROVE** → 選擇『APPROVE，進入 QA 審核』\n"
                        "- 若包含 **決策：RETURN_TO_PM** → 選擇『RETURN_TO_PM，退回 PM 修改』"
                    ),
                    "options": [
                        {
                            "label": "APPROVE，進入 QA 審核",
                            "target_step": "qa_review",
                            "condition_hint": "技術規格已完成，無重大可行性問題"
                        },
                        {
                            "label": "RETURN_TO_PM，退回 PM 修改",
                            "target_step": "pm_revise",
                            "condition_hint": "PM Spec 有技術問題需修正"
                        }
                    ]
                },
                "loop": {
                    "enabled": True,
                    "max_iterations": 2,
                    "escalate_to": "qa_review"
                }
            },
            # ── Step 3: PM 根據 Architect 意見修改 Spec ──────────────────────
            {
                "id": "pm_revise",
                "agent_role": "pm",
                "task_type": "revise",
                "depends_on": ["architect_review"],
                "routing": {
                    "type": "static",
                    "next_steps": ["architect_review"]
                },
                "loop": {
                    "enabled": True,
                    "max_iterations": 2,
                    "escalate_to": "qa_review"
                }
            },
            # ── Step 4: QA 審核，審核通過時產出 QA Checklist ─────────────────
            {
                "id": "qa_review",
                "agent_role": "qa",
                "task_type": "review",
                "depends_on": ["architect_review"],
                "routing": {
                    "type": "llm_decision",
                    "decision_prompt": (
                        "根據 QA 文件最末的決策標記判斷路由：\n"
                        "- 若包含 **決策：APPROVE** → 選擇『APPROVE，進入 Director 審批』\n"
                        "- 若包含 **決策：RETURN_TO_PM** → 選擇『RETURN_TO_PM，退回 PM 修改』"
                    ),
                    "options": [
                        {
                            "label": "APPROVE，進入 Director 審批",
                            "target_step": "director_approve",
                            "condition_hint": "QA Checklist 已產出，spec 可測試性足夠"
                        },
                        {
                            "label": "RETURN_TO_PM，退回 PM 修改",
                            "target_step": "pm_revise_2",
                            "condition_hint": "驗收標準不清或範圍邊界不明"
                        }
                    ]
                },
                "loop": {
                    "enabled": True,
                    "max_iterations": 2,
                    "escalate_to": "director_approve"
                }
            },
            # ── Step 5: PM 根據 QA 意見修改 Spec ────────────────────────────
            {
                "id": "pm_revise_2",
                "agent_role": "pm",
                "task_type": "revise",
                "depends_on": ["qa_review"],
                "routing": {
                    "type": "static",
                    "next_steps": ["qa_review"]
                },
                "loop": {
                    "enabled": True,
                    "max_iterations": 2,
                    "escalate_to": "director_approve"
                }
            },
            # ── Step 6: Director 最終商業決策審批 ────────────────────────────
            {
                "id": "director_approve",
                "agent_role": "director",
                "task_type": "approve",
                "depends_on": ["qa_review"],
                "routing": {
                    "type": "llm_decision",
                    "decision_prompt": (
                        "Director 站在商業與策略角度做最終決策：\n"
                        "- 若整體方向、ROI、風險皆可接受 → 選擇『APPROVE，產出文件』\n"
                        "- 若有重大商業或策略問題 → 選擇『REJECT，退回 PM 修改』"
                    ),
                    "options": [
                        {
                            "label": "APPROVE，產出文件",
                            "target_step": "export",
                            "condition_hint": "商業目標清晰，風險可控，批准交付"
                        },
                        {
                            "label": "REJECT，退回 PM 修改",
                            "target_step": "pm_revise_final",
                            "condition_hint": "商業方向或優先順序需要調整"
                        }
                    ]
                }
            },
            # ── Step 7: PM 根據 Director 意見做最終修改 ──────────────────────
            {
                "id": "pm_revise_final",
                "agent_role": "pm",
                "task_type": "revise",
                "depends_on": ["director_approve"],
                "routing": {
                    "type": "static",
                    "next_steps": ["director_approve"]
                },
                "loop": {
                    "enabled": True,
                    "max_iterations": 2,
                    "escalate_to": "export"
                }
            },
            # ── Step 8: 完成，標記輸出 ───────────────────────────────────────
            {
                "id": "export",
                "agent_role": "system",
                "task_type": "export",
                "depends_on": ["director_approve"],
                "routing": {
                    "type": "static",
                    "next_steps": []
                }
            }
        ],
        "guardrails": {
            "max_total_steps": 30,
            "timeout_minutes": 45,
            "require_human_approval": ["director_approve"]
        }
    }
}

QUICK_REVIEW_TEMPLATE = {
    "workflow": {
        "id": "quick-review",
        "name": "快速 Review",
        "description": "PM 起草 → Director 直接審批，適合小變更",
        "version": 1,
        "steps": [
            {
                "id": "pm_draft",
                "agent_role": "pm",
                "task_type": "draft",
                "depends_on": [],
                "routing": {
                    "type": "static",
                    "next_steps": ["director_approve"]
                }
            },
            {
                "id": "director_approve", 
                "agent_role": "director",
                "task_type": "approve",
                "depends_on": ["pm_draft"],
                "routing": {
                    "type": "llm_decision",
                    "decision_prompt": "審核 PM 產出的品質，決定是否通過。",
                    "options": [
                        {
                            "label": "批准，產出文件",
                            "target_step": "export",
                            "condition_hint": "品質符合標準"
                        },
                        {
                            "label": "打回修改",
                            "target_step": "pm_revise", 
                            "condition_hint": "需要改善"
                        }
                    ]
                }
            },
            {
                "id": "pm_revise",
                "agent_role": "pm",
                "task_type": "revise", 
                "depends_on": ["director_approve"],
                "routing": {
                    "type": "static",
                    "next_steps": ["director_approve"]
                }
            },
            {
                "id": "export",
                "agent_role": "system",
                "task_type": "export",
                "depends_on": ["director_approve"],
                "routing": {
                    "type": "static", 
                    "next_steps": []
                }
            }
        ],
        "guardrails": {
            "max_total_steps": 10,
            "timeout_minutes": 10,
            "require_human_approval": []
        }
    }
}

FULL_DELIVERY_TEMPLATE = {
    "workflow": {
        "id": "full-delivery",
        "name": "完整交付流程",
        "description": "PM → Architect → DevOps → QA → Director，含所有角色的完整流程",
        "version": 1,
        "steps": [
            {
                "id": "pm_draft",
                "agent_role": "pm",
                "task_type": "draft",
                "depends_on": [],
                "routing": {
                    "type": "static",
                    "next_steps": ["architect_review", "devops_review"]  # 並行
                }
            },
            {
                "id": "architect_review",
                "agent_role": "architect", 
                "task_type": "review",
                "depends_on": ["pm_draft"],
                "routing": {
                    "type": "llm_decision",
                    "decision_prompt": "審核技術架構可行性",
                    "options": [
                        {
                            "label": "通過",
                            "target_step": "qa_checklist",
                            "condition_hint": "架構可行"
                        },
                        {
                            "label": "打回",
                            "target_step": "pm_revise",
                            "condition_hint": "需要修改"
                        }
                    ]
                },
                "loop": {
                    "enabled": True,
                    "max_iterations": 2,
                    "escalate_to": "director_approve"
                }
            },
            {
                "id": "devops_review",
                "agent_role": "devops",
                "task_type": "review",
                "depends_on": ["pm_draft"],
                "routing": {
                    "type": "static",
                    "next_steps": ["qa_checklist"]
                }
            },
            {
                "id": "pm_revise",
                "agent_role": "pm",
                "task_type": "revise",
                "depends_on": ["architect_review"],
                "routing": {
                    "type": "static",
                    "next_steps": ["architect_review"]
                }
            },
            {
                "id": "qa_checklist",
                "agent_role": "qa", 
                "task_type": "draft",
                "depends_on": ["architect_review", "devops_review"],  # 等兩個都完成
                "routing": {
                    "type": "static",
                    "next_steps": ["director_approve"]
                }
            },
            {
                "id": "director_approve",
                "agent_role": "director",
                "task_type": "approve",
                "depends_on": ["qa_checklist"],
                "routing": {
                    "type": "llm_decision",
                    "decision_prompt": "最終審核",
                    "options": [
                        {
                            "label": "批准", 
                            "target_step": "export",
                            "condition_hint": "品質達標"
                        },
                        {
                            "label": "需改善",
                            "target_step": "pm_revise",
                            "condition_hint": "需要修改"
                        }
                    ]
                }
            },
            {
                "id": "export",
                "agent_role": "system",
                "task_type": "export", 
                "depends_on": ["director_approve"],
                "routing": {
                    "type": "static",
                    "next_steps": []
                }
            }
        ],
        "guardrails": {
            "max_total_steps": 30,
            "timeout_minutes": 45,
            "require_human_approval": ["director_approve"]
        }
    }
}

PM_DIALOGUE_TEMPLATE = {
    "workflow": {
        "id": "pm-dialogue",
        "name": "PM 雙人協作流程",
        "description": "兩位 PM 互相對談至少 5 輪完善 Spec → Director 審核 → PM 最終修訂",
        "version": 1,
        "steps": [
            {
                "id": "pm_dialogue",
                "agent_role": "pm",
                "task_type": "dialogue",
                "config": {
                    "min_rounds": 2,
                    "max_rounds": 3,
                },
                "depends_on": [],
                "routing": {
                    "type": "static",
                    "next_steps": ["director_approve"]
                },
            },
            {
                "id": "director_approve",
                "agent_role": "director",
                "task_type": "approve",
                "depends_on": ["pm_dialogue"],
                "routing": {
                    "type": "llm_decision",
                    "decision_prompt": "審核 PM 雙人協作產出的 spec 品質。",
                    "options": [
                        {
                            "label": "批准，產出文件",
                            "target_step": "export",
                            "condition_hint": "品質達標，可以交付"
                        },
                        {
                            "label": "退回 PM 修改",
                            "target_step": "pm_revise",
                            "condition_hint": "仍有需要改善的地方"
                        }
                    ]
                }
            },
            {
                "id": "pm_revise",
                "agent_role": "pm",
                "task_type": "revise",
                "depends_on": ["director_approve"],
                "routing": {
                    "type": "static",
                    "next_steps": ["director_approve"]
                },
                "loop": {
                    "enabled": True,
                    "max_iterations": 2,
                    "escalate_to": "export"
                }
            },
            {
                "id": "export",
                "agent_role": "system",
                "task_type": "export",
                "depends_on": ["director_approve"],
                "routing": {
                    "type": "static",
                    "next_steps": []
                }
            }
        ],
        "guardrails": {
            "max_total_steps": 25,
            "timeout_minutes": 60,
            "require_human_approval": ["director_approve"]
        }
    }
}

DEFAULT_TEMPLATES = [
    STANDARD_SPEC_TEMPLATE,
    QUICK_REVIEW_TEMPLATE,
    FULL_DELIVERY_TEMPLATE,
    PM_DIALOGUE_TEMPLATE,
]