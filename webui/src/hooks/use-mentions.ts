import { useState, useEffect, useCallback, useMemo } from 'react';
import { api, type Skill } from '../lib/api';

export interface MentionState {
  isOpen: boolean;
  search: string;
  position: number;
  caretPosition: { top: number; left: number } | null;
}

export function useMentions(textareaRef: React.RefObject<HTMLTextAreaElement | null>) {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [mentionState, setMentionState] = useState<MentionState>({
    isOpen: false,
    search: '',
    position: -1,
    caretPosition: null,
  });
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Load skills on mount
  useEffect(() => {
    const loadSkills = async () => {
      try {
        const result = await api.listSkills();
        setSkills(result.skills);
      } catch (error) {
        console.error('Failed to load skills:', error);
      }
    };
    loadSkills();
  }, []);

  // Filter skills based on search
  const filteredSkills = useMemo(() => {
    if (!mentionState.search) return skills;
    const searchLower = mentionState.search.toLowerCase();
    return skills.filter(skill => 
      skill.name.toLowerCase().includes(searchLower)
    );
  }, [skills, mentionState.search]);

  // Reset selected index when filtered skills change
  useEffect(() => {
    setSelectedIndex(0);
  }, [filteredSkills.length]);

  // Calculate caret position for dropdown
  const getCaretCoordinates = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return null;

    // Create a mirror div to calculate caret position
    const mirror = document.createElement('div');
    const computed = window.getComputedStyle(textarea);
    
    // Copy styles
    Array.from(computed).forEach(prop => {
      mirror.style[prop as any] = computed.getPropertyValue(prop);
    });
    
    mirror.style.position = 'absolute';
    mirror.style.visibility = 'hidden';
    mirror.style.whiteSpace = 'pre-wrap';
    mirror.style.wordWrap = 'break-word';
    
    document.body.appendChild(mirror);
    
    // Get text up to caret
    const textBeforeCaret = textarea.value.substring(0, textarea.selectionStart);
    mirror.textContent = textBeforeCaret;
    
    // Create a span for the caret position
    const span = document.createElement('span');
    span.textContent = '|';
    mirror.appendChild(span);
    
    const rect = textarea.getBoundingClientRect();
    const spanRect = span.getBoundingClientRect();
    
    document.body.removeChild(mirror);
    
    return {
      top: spanRect.top - rect.top + textarea.scrollTop,
      left: spanRect.left - rect.left,
    };
  }, [textareaRef]);

  // Detect @ mention trigger
  const handleInputChange = useCallback((value: string, cursorPosition: number) => {
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    
    // Check if we're in a mention context
    if (lastAtIndex !== -1) {
      const textAfterAt = textBeforeCursor.substring(lastAtIndex + 1);
      // Only trigger if no space after @ (we're still typing the mention)
      if (!textAfterAt.includes(' ')) {
        const caretPosition = getCaretCoordinates();
        setMentionState({
          isOpen: true,
          search: textAfterAt,
          position: lastAtIndex,
          caretPosition,
        });
        setSelectedIndex(0);
        return;
      }
    }
    
    // Close mention dropdown
    if (mentionState.isOpen) {
      setMentionState({
        isOpen: false,
        search: '',
        position: -1,
        caretPosition: null,
      });
    }
  }, [mentionState.isOpen, getCaretCoordinates]);

  // Insert selected skill mention
  const insertMention = useCallback((skill: Skill, currentValue: string): string => {
    if (mentionState.position === -1) return currentValue;
    
    const before = currentValue.substring(0, mentionState.position);
    const after = currentValue.substring(mentionState.position + 1 + mentionState.search.length);
    
    return `${before}@${skill.name} ${after}`;
  }, [mentionState]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>, currentValue: string, onChange: (value: string) => void): boolean => {
    if (!mentionState.isOpen || filteredSkills.length === 0) return false;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, filteredSkills.length - 1));
        return true;
      
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
        return true;
      
      case 'Enter':
      case 'Tab':
        e.preventDefault();
        const selectedSkill = filteredSkills[selectedIndex];
        if (selectedSkill) {
          const newValue = insertMention(selectedSkill, currentValue);
          onChange(newValue);
          setMentionState({
            isOpen: false,
            search: '',
            position: -1,
            caretPosition: null,
          });
        }
        return true;
      
      case 'Escape':
        e.preventDefault();
        setMentionState({
          isOpen: false,
          search: '',
          position: -1,
          caretPosition: null,
        });
        return true;
      
      default:
        return false;
    }
  }, [mentionState.isOpen, filteredSkills, selectedIndex, insertMention]);

  // Close mention dropdown
  const closeMentions = useCallback(() => {
    setMentionState({
      isOpen: false,
      search: '',
      position: -1,
      caretPosition: null,
    });
  }, []);

  // Select mention by click
  const selectMention = useCallback((skill: Skill, currentValue: string, onChange: (value: string) => void) => {
    const newValue = insertMention(skill, currentValue);
    onChange(newValue);
    closeMentions();
    // Focus back to textarea
    textareaRef.current?.focus();
  }, [insertMention, closeMentions, textareaRef]);

  return {
    mentionState,
    filteredSkills,
    selectedIndex,
    setSelectedIndex,
    handleInputChange,
    handleKeyDown,
    selectMention,
    closeMentions,
  };
}
