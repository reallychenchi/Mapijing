import React from 'react';
import type { EmotionType } from '../../types/emotion';
import { AVATAR_MAP } from '../../types/emotion';
import { EarIndicator } from './EarIndicator';
import './AvatarArea.css';

export interface AvatarAreaProps {
  emotion: EmotionType;
  showEarIndicator: boolean;
  isEarBlinking: boolean;
}

export const AvatarArea: React.FC<AvatarAreaProps> = ({
  emotion,
  showEarIndicator,
  isEarBlinking,
}) => {
  const avatarSrc = AVATAR_MAP[emotion];

  return (
    <div className="avatar-area">
      <div className="avatar-container">
        <img
          src={avatarSrc}
          alt={`虚拟人头像 - ${emotion}`}
          className="avatar-image"
        />
        {showEarIndicator && <EarIndicator isBlinking={isEarBlinking} />}
      </div>
    </div>
  );
};
