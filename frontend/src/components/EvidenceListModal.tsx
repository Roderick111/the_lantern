/**
 * EvidenceListModal Component
 *
 * Modal wrapping EvidenceBoard for sidebar-triggered display.
 * Uses shared Modal component for consistent design with Spell Book.
 *
 * @module components/EvidenceListModal
 */

import { Modal } from './ui/Modal';
import { EvidenceBoard } from './EvidenceBoard';

// ============================================
// Types
// ============================================

interface EvidenceListModalProps {
  isOpen: boolean;
  onClose: () => void;
  evidence: string[];
  evidenceNames?: Record<string, string>;
  caseId: string;
  onEvidenceClick: (id: string) => void;
}

// ============================================
// Component
// ============================================

export function EvidenceListModal({
  isOpen,
  onClose,
  evidence,
  evidenceNames,
  caseId,
  onEvidenceClick,
}: EvidenceListModalProps) {
  const handleEvidenceClick = (id: string) => {
    onEvidenceClick(id);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="EVIDENCE BOARD"
      variant="terminal"
      maxWidth="max-w-md"
    >
      <EvidenceBoard
        evidence={evidence}
        evidenceNames={evidenceNames}
        caseId={caseId}
        onEvidenceClick={handleEvidenceClick}
        collapsible={false}
        compact={false}
        bare={true}
      />
    </Modal>
  );
}
