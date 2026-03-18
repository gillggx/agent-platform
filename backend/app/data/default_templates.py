"""Default workflow templates"""

STANDARD_SPEC_TEMPLATE = {
    "workflow": {
        "id": "standard-spec",
        "name": "標準 Spec 流程",
        "description": "PM 起草 → Architect 技術審核 → QA 建立測試 → Director 最終審批",
        "version": 1,
        "steps": [
            {
                "id": "pm_draft",
                "agent_role": "pm",
                "task_type": "draft",
                "depends_on": [],
                "routing": {
                    "type": "static",
                    "next_steps": ["architect_review"]
                },
                "loop": {
                    "enabled": True,
                    "max_iterations": 2,
                    "escalate_to": "director_approve"
                }
            },
            {
                "id": "architect_review",
                "agent_role": "architect",
                "task_type": "review",
                "depends_on": ["pm_draft"],
                "routing": {
                    "type": "llm_decision",
                    "decision_prompt": "Review PM 的 spec，判斷技術可行性。",
                    "options": [
                        {
                            "label": "通過，進入 QA",
                            "target_step": "qa_checklist",
                            "condition_hint": "技術方案可行，無重大問題"
                        },
                        {
                            "label": "打回 PM 修改",
                            "target_step": "pm_revise",
                            "condition_hint": "有技術問題需要 PM 調整需求"
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
                "depends_on": ["architect_review"],
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
                    "decision_prompt": "最終審核所有產出物的品質與完整度。",
                    "options": [
                        {
                            "label": "批准，產出文件", 
                            "target_step": "export",
                            "condition_hint": "所有文件品質達標"
                        },
                        {
                            "label": "需要修改",
                            "target_step": "pm_revise", 
                            "condition_hint": "仍有需要改善的地方"
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
            "max_total_steps": 20,
            "timeout_minutes": 30,
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