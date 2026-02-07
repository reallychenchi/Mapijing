import React from 'react';
import type { EmotionType } from '../../types/emotion';
import { AVATAR_MAP } from '../../types/emotion';
import { EarIndicator } from './EarIndicator';
import './AvatarArea.css';

export interface AvatarAreaProps {
  emotion: EmotionType;
  showEarIndicator: boolean;
  isEarBlinking: boolean;
  onClick?: () => void;
}

export const AvatarArea: React.FC<AvatarAreaProps> = ({
  emotion,
  showEarIndicator,
  isEarBlinking,
  onClick,
}) => {
  const avatarSrc = AVATAR_MAP[emotion];

  return (
    <div className="avatar-area">
      <div
        className="avatar-container"
        onClick={onClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            onClick?.();
          }
        }}
        role="button"
        tabIndex={0}
        style={{ cursor: onClick ? 'pointer' : 'default' }}
      >
        <img src={avatarSrc} alt={`虚拟人头像 - ${emotion}`} className="avatar-image" />
        {showEarIndicator && <EarIndicator isBlinking={isEarBlinking} />}
      </div>
    </div>
  );
};
